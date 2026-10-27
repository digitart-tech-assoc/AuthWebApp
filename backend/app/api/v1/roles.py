"""役割: Discordロール取得API"""
from __future__ import annotations

import asyncio
import bisect
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

from app.core.auth import require_admin, require_member
from app.db.audit_repository import (
	ACTION_CREATE,
	ACTION_DELETE,
	ACTION_REORDER,
	ACTION_ROLLBACK,
	ACTION_UPDATE,
	OP_PUSH,
	OP_SELF_BATCH,
	OP_SELF_CREATE,
	SYSTEM_DISCORD,
	TARGET_MEMBER_ROLES,
	TARGET_ROLE,
	AuditContext,
	AuditLog,
	assignment_diff,
	get_audit_context,
	record_discord_audit_safely,
)
from app.core.errors import describe_exception
from app.core.config import (
	ADMIN_ROLE_NAMES,
	DISCORD_API_TIMEOUT,
	MEMBER_RESTRICTED_CATEGORY_NAMES,
	MEMBER_ROLE_NAMES,
	OBOG_ROLE_NAMES,
	PRE_MEMBER_ROLE_NAME,
	ROLE_SELF_CREATE_RATE_LIMIT,
	ROLE_SELF_CREATE_RATE_WINDOW_SECONDS,
	SUB_USER_ROLE_NAMES,
)
from app.core.rate_limit import SlidingWindowRateLimiter, enforce_rate_limit
from app.db.manifest_repository import (
	RoleNameConflictError,
	insert_member_created_role,
	normalize_role_name,
)
from app.db.repository import (
	batch_update_user_roles,
	fetch_guild_members,
	fetch_manifest,
	fetch_role_assignments,
	fetch_role_assignments_for_user,
	get_member_lists,
	save_guild_members,
	sync_member_lists,
	update_role_id,
)
from app.services.discord_client import (
	DiscordAPIError,
	add_role_to_member,
	build_role_create_payload,
	build_role_edit_payload,
	create_guild_role,
	delete_guild_role,
	edit_guild_role,
	fetch_all_guild_members,
	fetch_bot_guilds,
	fetch_bot_guild_member,
	fetch_guild_member,
	fetch_guild_roles,
	fetch_role_ids_with_channel_permissions,
	redact_snowflakes,
	remove_role_from_member,
	reorder_guild_roles,
	set_member_roles,
)


router = APIRouter(prefix="/api/v1/roles", tags=["roles"])
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
DISCORD_BOT_URL = os.getenv("DISCORD_BOT_URL", "http://discord-bot:8000")
# 監査ログに記録する Discord のロール定義のフィールド（fetch_guild_roles の戻り値の形式）
DISCORD_ROLE_AUDIT_FIELDS = ("name", "color", "hoist", "mentionable", "permissions", "position")
SHARED_SECRET = os.getenv("SHARED_SECRET", "")
_self_create_limiter = SlidingWindowRateLimiter(ROLE_SELF_CREATE_RATE_LIMIT, ROLE_SELF_CREATE_RATE_WINDOW_SECONDS)


def _get_token() -> str:
	return DISCORD_TOKEN.strip()


async def _notify_bot_to_reconcile() -> bool:
	"""Discord Bot に対して reconcile を実行するよう要求する。
	
	成功した場合は True を返す。失敗した場合はログして False を返す。
	"""
	try:
		async with httpx.AsyncClient(timeout=10.0) as client:
			resp = await client.post(
				f"{DISCORD_BOT_URL}/internal/sync",
				json={"action": "sync_roles"},
				headers={"Authorization": f"Bearer {SHARED_SECRET}"},
			)
			if resp.status_code == 200:
				# reconcile の errors には Discord ID が含まれるため、件数だけを出す
				summary = resp.json().get("result", {})
				logger.info(
					"Bot reconcile triggered successfully: added=%s, removed=%s, errors=%d",
					summary.get("added"), summary.get("removed"), len(summary.get("errors") or []),
				)
				return True
			else:
				logger.warning("Bot reconcile failed with status %d: %s", resp.status_code, resp.text)
				return False
	except Exception as e:
		logger.warning("Failed to trigger bot reconcile: %s", e)
		return False


async def _sync_role_definitions(
	desired_roles: list[dict],
	actual_roles: list[dict],
	token: str,
	audit: AuditContext | None = None,
) -> tuple[int, int, int, int, set[str], set[str], list[str], dict, dict]:
	"""ロール定義の同期（Create / Update / Delete）

	Discord のロールを変更するたびに、その場で監査ログに記録する（記録に失敗しても続行する）。
	"""
	actual_by_id = {role["role_id"]: role for role in actual_roles}
	desired_by_id = {role["role_id"]: role for role in desired_roles}

	updated = 0
	created = 0
	deleted = 0
	skipped_managed = 0
	errors: list[str] = []
	created_real_ids: set[str] = set()
	deleted_role_ids: set[str] = set()

	for role in desired_roles:
		role_id = role["role_id"]
		actual = actual_by_id.get(role_id)
		if actual is None:
			try:
				new_role_discord = await create_guild_role(DISCORD_GUILD_ID, token, build_role_create_payload(role))
				created += 1
				real_id = new_role_discord["role_id"]
				await record_discord_audit_safely(audit, [AuditLog(
					SYSTEM_DISCORD, TARGET_ROLE, real_id, ACTION_CREATE,
					None, {f: new_role_discord.get(f) for f in DISCORD_ROLE_AUDIT_FIELDS},
				)])
				if str(role_id).startswith("draft-"):
					await asyncio.to_thread(update_role_id, role_id, real_id, audit)
					desired_by_id[real_id] = role
					role["role_id"] = real_id
					actual_by_id[real_id] = new_role_discord
					created_real_ids.add(real_id)
			except Exception as exc:
				msg = f"Failed to create role {role_id} ({describe_exception(exc)})"
				_log_push_error("create role", exc, target_id=role_id)
				errors.append(msg)
			continue
		if actual.get("managed") or role_id == DISCORD_GUILD_ID:
			skipped_managed += 1
			continue
		payload = build_role_edit_payload(role, actual)
		if not payload:
			continue
		try:
			await edit_guild_role(DISCORD_GUILD_ID, role_id, token, payload)
			updated += 1
			# 記録するのは実際に送ったフィールドだけ。値は送信形式ではなく fetch_guild_roles / fetch_manifest の形式で残す
			await record_discord_audit_safely(audit, [AuditLog(
				SYSTEM_DISCORD, TARGET_ROLE, role_id, ACTION_UPDATE,
				{f: actual.get(f) for f in payload},
				{f: role.get(f) for f in payload},
			)])
		except Exception as exc:
			msg = f"Failed to update role {role_id} ({describe_exception(exc)})"
			_log_push_error("update role", exc, target_id=role_id)
			errors.append(msg)

	for role in actual_roles:
		role_id = role["role_id"]
		if role_id in desired_by_id:
			continue
		if role.get("managed") or role_id == DISCORD_GUILD_ID:
			continue
		try:
			await delete_guild_role(DISCORD_GUILD_ID, role_id, token)
			deleted += 1
			deleted_role_ids.add(role_id)
			await record_discord_audit_safely(audit, [AuditLog(
				SYSTEM_DISCORD, TARGET_ROLE, role_id, ACTION_DELETE,
				{f: role.get(f) for f in DISCORD_ROLE_AUDIT_FIELDS}, None,
			)])
		except Exception as exc:
			msg = f"Failed to delete role {role_id} ({describe_exception(exc)})"
			_log_push_error("delete role", exc, target_id=role_id)
			errors.append(msg)

	return (
		updated, created, deleted, skipped_managed,
		created_real_ids, deleted_role_ids, errors,
		actual_by_id, desired_by_id
	)


def _moved_role_ids(position_payload: list[dict], actual_by_id: dict, created_real_ids: set[str]) -> set[str]:
	"""並び替えで、ほかのロールとの相対的な順序が変わるロールの ID を返す。

	Discord の position の値そのものは比べない。ロールを作成すると既存ロールの position が一律にずれるため、
	値で比べると並び順を変えていないロールまで数えてしまう。
	push 前の並び順と送信する並び順を比べ、順序を保ったまま残せる最大のロール（最長増加部分列）以外を
	「並び替えたロール」とする。今回作成したロールは created で数えるため含めない。
	最長増加部分列が複数ある場合は、下の復元方法で決まる1つを使う（どのロールを並び替えたとみなすかは一意ではない）。
	"""
	existing_ids = [p["id"] for p in position_payload if p["id"] not in created_real_ids]

	def _current_order_key(role_id: str) -> tuple[int, int]:
		# position が同じロールは ID 順に並ぶ（推定）
		return (int(actual_by_id[role_id].get("position", 0)), int(role_id) if role_id.isdigit() else 0)

	current_rank = {rid: rank for rank, rid in enumerate(sorted(existing_ids, key=_current_order_key))}
	ranks = [current_rank[rid] for rid in existing_ids]
	# 最長増加部分列（各長さの部分列の末尾の最小値と、その添字を保持し、前の要素をたどって復元する）
	tails: list[int] = []
	tail_indexes: list[int] = []
	previous: list[int] = [-1] * len(ranks)
	for i, rank in enumerate(ranks):
		index = bisect.bisect_left(tails, rank)
		previous[i] = tail_indexes[index - 1] if index > 0 else -1
		if index == len(tails):
			tails.append(rank)
			tail_indexes.append(i)
		else:
			tails[index] = rank
			tail_indexes[index] = i
	kept: set[str] = set()
	i = tail_indexes[-1] if tail_indexes else -1
	while i >= 0:
		kept.add(existing_ids[i])
		i = previous[i]
	return set(existing_ids) - kept


async def _reorder_roles(
	desired_roles: list[dict],
	actual_by_id: dict,
	created_real_ids: set[str],
	token: str,
	audit: AuditContext | None = None,
) -> tuple[int, list[str]]:
	"""ロール順序の再編成（contiguous 1..N positions）

	返す件数は、並び順が変わったロールの数（_moved_role_ids を参照）。送信したロールの数ではない。
	監査ログには、並び順が変わったロールだけを1ロール1行で記録する。
	"""
	errors: list[str] = []
	desired_roles_sorted = sorted(desired_roles, key=lambda x: int(x.get("position", 0)))
	position_payload = []
	current_pos = 1
	for role in desired_roles_sorted:
		rid = role["role_id"]
		if rid == DISCORD_GUILD_ID:
			continue
		if rid in actual_by_id or rid in created_real_ids:
			position_payload.append({"id": rid, "position": current_pos})
			current_pos += 1
	reordered = 0
	if position_payload:
		try:
			await reorder_guild_roles(DISCORD_GUILD_ID, token, position_payload)
			moved_ids = _moved_role_ids(position_payload, actual_by_id, created_real_ids)
			reordered = len(moved_ids)
			sent_positions = {p["id"]: p["position"] for p in position_payload}
			await record_discord_audit_safely(audit, [
				AuditLog(
					SYSTEM_DISCORD, TARGET_ROLE, rid, ACTION_REORDER,
					{"position": actual_by_id[rid].get("position")}, {"position": sent_positions[rid]},
				)
				for rid in sorted(moved_ids)
			])
		except Exception as exc:
			msg = f"Failed to reorder roles ({describe_exception(exc)})"
			_log_push_error("reorder roles", exc)
			errors.append(msg)
			reordered = 0
	return reordered, errors


async def _apply_role_assignment_diffs(
	actual_by_id: dict,
	created_real_ids: set[str],
	deleted_role_ids: set[str],
	token: str,
	audit: AuditContext | None = None,
) -> tuple[int, int, int, list[str]]:
	"""メンバーロール割り当ての差分適用

	差分はメンバー単位にまとめて反映する（反映方法は _apply_member_role_diff を参照）。
	PATCH はロール一覧を丸ごと上書きするため、Discord 上の現在のロールを元に設定後の一覧を組み立て、
	差分の対象外のロール（managed や DB 未登録のロール等）はそのまま残す。
	"""
	assigned_adds = 0
	assigned_removes = 0
	skipped_members = 0
	errors: list[str] = []

	try:
		async with httpx.AsyncClient(timeout=DISCORD_API_TIMEOUT) as client:
			desired_assignments = await asyncio.to_thread(fetch_role_assignments)
			current_members = await fetch_all_guild_members(DISCORD_GUILD_ID, token, client=client)
			try:
				bot_member = await fetch_bot_guild_member(DISCORD_GUILD_ID, token, client=client)
			except Exception as exc:
				_log_push_error("fetch bot member; skipping role assignments", exc, level=logging.WARNING)
				bot_member = None
			# 並び替え後のロール階層で Bot が操作できるかを判定するため、ロール一覧を取得し直す
			try:
				latest_roles = await fetch_guild_roles(DISCORD_GUILD_ID, token, client=client)
				roles_refetched = True
			except Exception as exc:
				# ロール一覧の再取得に失敗した場合は push 開始時のロール一覧を使う。
				_log_push_error("refetch guild roles; using roles fetched before sync", exc, level=logging.WARNING)
				latest_roles = list(actual_by_id.values())
				roles_refetched = False
			manageable_role_ids = _manageable_role_ids(latest_roles, bot_member)
			if _bot_top_role_position(latest_roles, bot_member) is None:
				logger.warning("Skipped role assignments because the bot's highest role could not be determined")
				errors.append("Skipped role assignments because the bot's highest role could not be determined")
			elif not roles_refetched:
				# 再取得に失敗した場合、新規ロールは push 開始時の一覧に含まれない。
				manageable_role_ids |= created_real_ids

			current_by_role: dict[str, set[str]] = {}
			for m in current_members:
				for rid in m.get("role_ids", []):
					current_by_role.setdefault(rid, set()).add(m["user_id"])
			desired_by_role = {rid: set(users) for rid, users in desired_assignments.items()}

			target_role_ids: set[str] = set()
			for role_id in set(desired_by_role) | set(current_by_role):
				if role_id == DISCORD_GUILD_ID or role_id.startswith("draft-"):
					continue
				if role_id not in actual_by_id and role_id not in created_real_ids:
					continue
				if role_id in deleted_role_ids:
					continue
				if role_id not in manageable_role_ids:
					# PATCH は 1 件でも操作できないロールを含むとメンバー全体が 403 になるため、差分から除く
					if desired_by_role.get(role_id, set()) != current_by_role.get(role_id, set()):
						logger.warning("Skipped role %s: managed or not lower than the bot role", role_id)
					continue
				target_role_ids.add(role_id)

			member_ids = {m["user_id"] for m in current_members}
			missing_members = {
				user_id
				for rid in target_role_ids
				for user_id in desired_by_role.get(rid, set())
				if user_id not in member_ids
			}
			skipped_members = len(missing_members)
			if missing_members:
				logger.warning("Skipped %d assigned users who are not in the guild", len(missing_members))

			pending: list[tuple[str, set[str], set[str], set[str]]] = []
			for m in sorted(current_members, key=lambda member: member["user_id"]):
				user_id = m["user_id"]
				current_roles = set(m.get("role_ids", []))
				desired_roles = {rid for rid in target_role_ids if user_id in desired_by_role.get(rid, set())}
				adds = desired_roles - current_roles
				removes = (current_roles & target_role_ids) - desired_roles
				if adds or removes:
					pending.append((user_id, current_roles, adds, removes))

			for index, (user_id, current_roles, adds, removes) in enumerate(pending):
				try:
					added, removed = await _apply_member_role_diff(
						user_id, current_roles, target_role_ids, token, client, audit
					)
					assigned_adds += added
					assigned_removes += removed
				except (DiscordAPIError, httpx.HTTPStatusError) as e:
					status_code = _error_status_code(e)
					if status_code == 429:
						# 再試行しても 429 のままなら、続けて送っても 429 を重ねるだけで、Discord の
						# 無効リクエスト数の上限（超えると IP 単位で一時的に遮断される）に近づくため、残りは送らない
						remaining = len(pending) - index
						msg = (
							f"Discord rate limited (HTTP 429); aborted updating roles for the remaining {remaining} members. "
							"Run push again later"
						)
						logger.warning("%s", msg)
						errors.append(msg)
						break
					if status_code == 404:
						# 開始時のメンバー一覧取得後にギルドを抜けたメンバー
						logger.warning(
							"Skipped updating roles for a member (+%d/-%d): HTTP 404",
							len(adds), len(removes),
						)
						continue
					if status_code == 403:
						# 1 件でも操作できないロールがあると、そのメンバーの差分がすべて反映されないため errors に残す。
						# レスポンスに含まれるため Discord ID は入れない
						msg = (
							f"Failed to update roles for a member (+{len(adds)}/-{len(removes)}): HTTP 403 "
							"(check the bot's Manage Roles permission and role hierarchy)"
						)
						logger.warning("%s", msg)
						errors.append(msg)
						continue
					# errors はレスポンスに含まれるため、例外メッセージ（Discord の応答本文・送信内容）は入れない。
					# 詳細は _log_push_error でログに出す
					_log_push_error("update member roles", e)
					errors.append(
						f"Failed to update roles for {user_id} (+{len(adds)}/-{len(removes)}): {describe_exception(e)}"
					)
				except Exception as exc:
					_log_push_error("update member roles", exc)
					errors.append(
						f"Failed to update roles for {user_id} (+{len(adds)}/-{len(removes)}): {describe_exception(exc)}"
					)
	except Exception as exc:
		_log_push_error("apply role assignment diffs", exc)
		errors.append(f"Failed to apply assignment diffs ({describe_exception(exc)})")

	return assigned_adds, assigned_removes, skipped_members, errors


async def _apply_member_role_diff(
	user_id: str,
	current_roles: set[str],
	target_role_ids: set[str],
	token: str,
	client: httpx.AsyncClient,
	audit: AuditContext | None = None,
) -> tuple[int, int]:
	"""1 メンバー分のロール差分を Discord に反映し、(追加数, 削除数) を返す。

	push 開始時に取得した DB の割り当てと Discord のロールを元にすると、その後に self-batch などで
	付与・解除されたロールを巻き戻してしまう。これを避けるため、
	- 反映の直前に、そのメンバーの DB の割り当てを読み直して、あるべきロールを決め直す
	- 差分が 1 件だけなら、ほかのロールに触れない PUT / DELETE で反映する（同じ状態への PUT / DELETE は変化しない）
	- 2 件以上なら、PATCH の直前にメンバーの現在のロールを取り直し、差分を計算し直して反映する
	いずれも Discord API の呼び出しは、ロールごとに PUT / DELETE する場合の回数以下になる。
	"""
	latest_assignments = await asyncio.to_thread(fetch_role_assignments_for_user, user_id)
	desired_roles = {rid for rid in latest_assignments if rid in target_role_ids}
	adds = desired_roles - current_roles
	removes = (current_roles & target_role_ids) - desired_roles
	if not adds and not removes:
		return 0, 0

	if len(adds) + len(removes) == 1:
		if adds:
			await add_role_to_member(DISCORD_GUILD_ID, user_id, next(iter(adds)), token, client=client)
		else:
			await remove_role_from_member(DISCORD_GUILD_ID, user_id, next(iter(removes)), token, client=client)
		await _record_member_roles(audit, user_id, adds, removes)
		return len(adds), len(removes)

	member = await fetch_guild_member(DISCORD_GUILD_ID, user_id, token, client=client)
	if member is None:
		raise DiscordAPIError("Member not found", 404)
	latest_roles = set(member.get("role_ids", []))
	latest_adds = desired_roles - latest_roles
	latest_removes = (latest_roles & target_role_ids) - desired_roles
	if not latest_adds and not latest_removes:
		return 0, 0
	new_roles = (latest_roles - latest_removes) | latest_adds
	await set_member_roles(DISCORD_GUILD_ID, user_id, sorted(new_roles), token, client=client)
	await _record_member_roles(audit, user_id, latest_adds, latest_removes)
	return len(latest_adds), len(latest_removes)


async def _record_member_roles(
	audit: AuditContext | None,
	user_id: str,
	added: set[str],
	removed: set[str],
	action: str = ACTION_UPDATE,
) -> None:
	"""メンバーの Discord のロールの付け外しを監査ログに記録する（記録に失敗しても続行する）。"""
	after = assignment_diff(added, removed)
	if after is None:
		return
	await record_discord_audit_safely(audit, [AuditLog(SYSTEM_DISCORD, TARGET_MEMBER_ROLES, user_id, action, None, after)])


def _error_status_code(exc: Exception) -> int | None:
	"""Discord API 呼び出しの例外から HTTP ステータスを取り出す。"""
	if isinstance(exc, DiscordAPIError):
		return exc.status_code
	if isinstance(exc, httpx.HTTPStatusError):
		return exc.response.status_code if exc.response is not None else None
	return None


def _log_push_error(
	operation: str,
	exc: Exception,
	*,
	target_id: str | None = None,
	level: int = logging.ERROR,
) -> None:
	"""Push失敗を個人情報やDiscordの例外メッセージを含めずに記録する。"""
	status_code = _error_status_code(exc)
	target = f" for target {target_id}" if target_id is not None else ""
	if status_code is not None:
		logger.log(level, "Discord role push %s%s failed with HTTP %d", operation, target, status_code)
	else:
		logger.log(
			level,
			"Discord role push %s%s failed (%s)",
			operation,
			target,
			type(exc).__name__,
			exc_info=True,
		)


def _bot_top_role_position(roles: list[dict], bot_member: dict | None) -> int | None:
	"""Bot メンバーが持つロールのうち最上位の position を返す。"""
	if bot_member is None:
		return None
	bot_role_ids = set(bot_member.get("role_ids", []))
	positions = [
		role.get("position", 0)
		for role in roles
		if role.get("role_id") in bot_role_ids
	]
	return max(positions) if positions else None


def _manageable_role_ids(roles: list[dict], bot_member: dict | None) -> set[str]:
	"""Bot が付与・解除できるロール ID を返す。基準ロールを特定できない場合は全て拒否する。"""
	bot_position = _bot_top_role_position(roles, bot_member)
	if bot_position is None:
		return set()
	return {
		role["role_id"]
		for role in roles
		if not role.get("managed")
		and role["role_id"] != DISCORD_GUILD_ID
		and role.get("position", 0) < bot_position
	}


@router.post("/push")
async def push_roles_to_discord(
	_principal: dict = Depends(require_admin),
	audit: AuditContext = Depends(get_audit_context),
) -> dict:
	audit = audit.with_operation(OP_PUSH)
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	manifest = await asyncio.to_thread(fetch_manifest)
	desired_roles = manifest.get("roles", [])

	try:
		actual_roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
	except Exception as exc:  # noqa: BLE001
		logger.exception("Discord role push: fetch guild roles failed")
		raise HTTPException(status_code=502, detail="Failed to fetch roles from Discord") from exc

	(
		updated, created, deleted, skipped_managed,
		created_real_ids, deleted_role_ids, sync_errors,
		actual_by_id, desired_by_id
	) = await _sync_role_definitions(desired_roles, actual_roles, token, audit)

	reordered, reorder_errors = await _reorder_roles(
		desired_roles, actual_by_id, created_real_ids, token, audit
	)

	assigned_adds, assigned_removes, skipped_members, assign_errors = await _apply_role_assignment_diffs(
		actual_by_id, created_real_ids, deleted_role_ids, token, audit
	)

	all_errors = sync_errors + reorder_errors + assign_errors
	logger.info("Discord role push completed with %d error(s): request_id=%s", len(all_errors), audit.request_id)

	# Notify Discord Bot to reconcile member_list / pre_member_list
	logger.debug("Notifying Discord Bot to reconcile member lists...")
	bot_reconciled = await _notify_bot_to_reconcile()

	return {
		"ok": len(all_errors) == 0,
		"guild_id": DISCORD_GUILD_ID,
		"updated": updated,
		"created": created,
		"deleted": deleted,
		"reordered": reordered,
		"skipped_managed": skipped_managed,
		"assigned_adds": assigned_adds,
		"assigned_removes": assigned_removes,
		"skipped_members": skipped_members,
		"bot_reconciled": bot_reconciled,
		"errors": all_errors,
	}


@router.get("/me/assignments")
async def get_my_role_assignments(_principal: dict = Depends(require_member)) -> dict:
	"""ログイン中のユーザー自身に割り当てられたロールだけを取得。"""
	discord_id = _principal.get("discord_id")
	if not discord_id:
		raise HTTPException(status_code=400, detail="Discord ID が特定できません。")

	assignments = await asyncio.to_thread(fetch_role_assignments_for_user, discord_id)
	return {"assignments": assignments}


@router.get("/members")
async def get_role_members(_principal: dict = Depends(require_admin)) -> dict:
	"""保存済みのギルドメンバー一覧とロール割り当てを取得。"""
	members = await asyncio.to_thread(fetch_guild_members)
	assignments = await asyncio.to_thread(fetch_role_assignments)
	return {"members": members, "assignments": assignments}


class PermissionsPayload(BaseModel):
	permissions: int


@router.patch("/{role_id}/permissions")
async def update_role_permissions(
	role_id: str,
	payload: PermissionsPayload,
	_principal: dict = Depends(require_admin),
) -> dict:
	"""特定ロールの権限を即時 Discord に反映（個別更新）。"""
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	try:
		await edit_guild_role(
			DISCORD_GUILD_ID,
			role_id,
			token,
			{"permissions": str(int(payload.permissions))},
		)
	except Exception as exc:  # noqa: BLE001
		logger.exception("Discord role permissions update failed")
		raise HTTPException(status_code=502, detail="Failed to update role permissions on Discord") from exc

	return {"ok": True, "role_id": role_id, "permissions": payload.permissions}


def _match_role_ids(roles: list[dict]) -> dict[str, Any]:
	"""Discordロール一覧から期待されるロール種別のIDを特定する"""
	member_role_ids = [r["role_id"] for r in roles if r["name"] in MEMBER_ROLE_NAMES]
	obog_role_ids = [r["role_id"] for r in roles if r["name"] in OBOG_ROLE_NAMES]
	admin_role_ids = [r["role_id"] for r in roles if r["name"] in ADMIN_ROLE_NAMES]
	pre_member_role_id = next((r["role_id"] for r in roles if r["name"] == PRE_MEMBER_ROLE_NAME), None)
	sub_user_role_ids = [r["role_id"] for r in roles if r["name"] in SUB_USER_ROLE_NAMES]

	all_matched = member_role_ids + obog_role_ids + admin_role_ids + sub_user_role_ids
	if pre_member_role_id:
		all_matched.append(pre_member_role_id)

	return {
		"member_role_ids": member_role_ids,
		"obog_role_ids": obog_role_ids,
		"admin_role_ids": admin_role_ids,
		"pre_member_role_id": pre_member_role_id,
		"sub_user_role_ids": sub_user_role_ids,
		"all_matched_role_ids": all_matched,
	}


@router.post("/members/sync")
async def sync_members_from_discord(_principal: dict = Depends(require_admin)) -> dict:
	"""Discord ギルドメンバーから member / sub_user / obog / admin / pre_member の user_memberships を差分同期する."""
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	try:
		logger.debug("sync_members: GUILD_ID=%s", DISCORD_GUILD_ID)
		
		# Get all roles from Discord
		roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
		logger.debug("Fetched %d roles from Discord", len(roles))
		for r in roles:
			logger.debug("  Role: %s (id=%s)", r['name'], r['role_id'])
		
		# Identify role IDs by name pattern (from app.core.config)
		matched = _match_role_ids(roles)
		member_role_ids = matched["member_role_ids"]
		obog_role_ids = matched["obog_role_ids"]
		admin_role_ids = matched["admin_role_ids"]
		pre_member_role_id = matched["pre_member_role_id"]
		sub_user_role_ids = matched["sub_user_role_ids"]
		all_matched_role_ids = matched["all_matched_role_ids"]
		
		logger.debug("Matched roles:")
		logger.debug("  member_role_ids=%s", member_role_ids)
		logger.debug("  obog_role_ids=%s", obog_role_ids)
		logger.debug("  admin_role_ids=%s", admin_role_ids)
		logger.debug("  pre_member_role_id=%s", pre_member_role_id)
		logger.debug("  sub_user_role_ids=%s", sub_user_role_ids)
		
		if not all_matched_role_ids:
			available_names = [r["name"] for r in roles]
			error_detail = (
				f"Failed to match Discord role names to expected roles. "
				f"Expected to find at least one of: member/会員/Member, OBOG/OB/OG/OB-OG, "
				f"administrator/管理者, pre-member, sub垢. "
				f"Available Discord role names: {available_names}"
			)
			logger.error("%s", error_detail)
			raise HTTPException(status_code=400, detail=error_detail)
		
		# ギルドの全メンバーを 1 回で取得し、ロールごとの所属メンバーはメンバーの role_ids から組み立てる。
		# 対象ロールを持たないメンバー（sub垢 のみのアカウントや Bot など）も guild_members に保存し、
		# /roles の表示や付与候補で名前・アイコンを引けるようにする
		guild_members = await fetch_all_guild_members(DISCORD_GUILD_ID, token)
		logger.debug("Fetched %d guild members", len(guild_members))
		# 0 件のまま同期すると全種別の行が削除されるため、取得失敗とみなして中止する
		# （Server Members Intent が無効な場合などに 0 件で返ることがある）
		if not guild_members:
			raise RuntimeError("Discord returned 0 guild members. Aborting sync to prevent data loss.")

		# 所属メンバーが 0 人のロールも空リストとして渡し、sync_member_lists の欠落チェックを通す
		members_data: dict[str, list[dict]] = {
			role_id: []
			for role_id in member_role_ids + obog_role_ids + admin_role_ids + sub_user_role_ids + ([pre_member_role_id] if pre_member_role_id else [])
		}
		for m in guild_members:
			for role_id in m.get("role_ids", []):
				if role_id in members_data:
					members_data[role_id].append(m)

		logger.debug("Saving %d guild members metadata", len(guild_members))
		await asyncio.to_thread(save_guild_members, guild_members)
		
		# Sync to DB
		logger.debug("Syncing role memberships to DB with members_data keys: %s", list(members_data.keys()))
		result = await asyncio.to_thread(
			sync_member_lists,
			member_role_ids,
			obog_role_ids,
			admin_role_ids,
			pre_member_role_id,
			members_data,
			sub_user_role_ids,
		)
		logger.debug("Sync result: %s", {key: len(rows) for key, rows in result.items()})
		
		return {
			"ok": True,
			"guild_id": DISCORD_GUILD_ID,
			"member_list": result["member_list"],
			"sub_user_list": result["sub_user_list"],
			"admin_list": result["admin_list"],
			"pre_member_list": result["pre_member_list"],
			"obog_list": result["obog_list"],
		}
	except HTTPException:
		raise
	except Exception as exc:  # noqa: BLE001
		logger.exception("Discord sync failed: %s", exc)
		raise HTTPException(status_code=502, detail="Discord sync failed") from exc


class SelfBatchPayload(BaseModel):
	roles_to_add: list[str] = Field(default_factory=list, max_length=50)
	roles_to_remove: list[str] = Field(default_factory=list, max_length=50)


def _self_assignable_category_ids(manifest: dict) -> set[str]:
	"""member が自分で扱えるロールのカテゴリ ID を返す。

	is_restricted = false と確認できたカテゴリのみ許可する。フラグ欠損時は拒否側に倒す。
	"""
	return {
		c["id"] for c in manifest.get("categories", [])
		if c["name"] not in MEMBER_RESTRICTED_CATEGORY_NAMES and not c.get("is_restricted", True)
	}


def _unwrap_discord_fetch(result: object, label: str):
	"""asyncio.gather(return_exceptions=True) の結果を取り出す。Discord API の失敗は 502 に変換する。"""
	if isinstance(result, Exception):
		logger.warning("Discord API call failed (%s)", label, exc_info=result)
		raise HTTPException(status_code=502, detail=f"Discord API error ({label})") from result
	if isinstance(result, BaseException):
		# キャンセル等は握りつぶさずそのまま送出する
		raise result
	return result


@router.post("/self-batch")
async def self_batch_roles(
	payload: SelfBatchPayload,
	_principal: dict = Depends(require_member),
	audit: AuditContext = Depends(get_audit_context),
) -> dict:
	"""memberが自分自身のロールを一括で付与・解除する。

	1. 全ロールを一括バリデーション（カテゴリ未設定・禁止カテゴリ・Discord権限付き）
	2. 現在の Discord ロール一覧を取得
	3. Discord の PATCH /members/{user_id} で1回の API 呼び出しで一括更新
	4. DB を一括更新
	5. Discord 更新後に DB 更新が失敗した場合はロールバック
	Discord・DB の変更と、Discord のロールバックを監査ログに記録する。
	"""
	audit = audit.with_operation(OP_SELF_BATCH)
	roles_to_add = set(payload.roles_to_add)
	roles_to_remove = set(payload.roles_to_remove)
	conflicting_role_ids = roles_to_add & roles_to_remove
	if conflicting_role_ids:
		raise HTTPException(
			status_code=400,
			detail=f"同じロールを付与と解除の両方に指定できません: {sorted(conflicting_role_ids)}",
		)

	all_role_ids = list(roles_to_add | roles_to_remove)
	if not all_role_ids:
		return {"ok": True, "added": [], "removed": [], "detail": "変更点はありませんでした"}

	discord_id: str | None = _principal.get("discord_id")
	if not discord_id:
		raise HTTPException(status_code=400, detail="Discord ID が特定できません。Discordアカウントで再ログインしてください。")

	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	# --- 1. 一括バリデーション（ホワイトリスト方式・DB のマニフェストを正とする） ---
	manifest = await asyncio.to_thread(fetch_manifest)
	roles_in_manifest = {r["role_id"]: r for r in manifest.get("roles", [])}
	self_assignable_cat_ids = _self_assignable_category_ids(manifest)

	for role_id in all_role_ids:
		role_info = roles_in_manifest.get(role_id)
		if role_info is None:
			raise HTTPException(status_code=404, detail=f"指定されたロール {role_id} が見つかりません")
		role_name = role_info.get("name", role_id)
		category_id = role_info.get("category_id")
		if category_id is None:
			raise HTTPException(
				status_code=403,
				detail=f"ロール '{role_name}' は変更できません（カテゴリ未設定）",
			)
		if category_id not in self_assignable_cat_ids:
			raise HTTPException(
				status_code=403,
				detail=f"ロール '{role_name}' は変更できません（禁止カテゴリ）",
			)
		if int(role_info.get("permissions", 0)) != 0:
			raise HTTPException(
				status_code=403,
				detail=f"ロール '{role_name}' は変更できません（Discord権限付き）",
			)

	# UIの表示制約に依存せず、Discord側のロール階層とmanagedフラグもAPIで検証する。
	# 付与時はチャンネル上書きも確認する。独立した取得は並列に実行する。
	fetches = [
		fetch_guild_roles(DISCORD_GUILD_ID, token),
		fetch_guild_member(DISCORD_GUILD_ID, discord_id, token),
		fetch_bot_guild_member(DISCORD_GUILD_ID, token),
	]
	if roles_to_add:
		fetches.append(fetch_role_ids_with_channel_permissions(DISCORD_GUILD_ID, token))
	fetch_results = await asyncio.gather(*fetches, return_exceptions=True)
	roles_result, member_result, bot_member_result = fetch_results[:3]
	discord_roles = _unwrap_discord_fetch(roles_result, "fetch roles")

	discord_roles_by_id = {role["role_id"]: role for role in discord_roles}
	bot_member = _unwrap_discord_fetch(bot_member_result, "fetch bot member")
	manageable_role_ids = _manageable_role_ids(discord_roles, bot_member)
	for role_id in all_role_ids:
		role_info = roles_in_manifest[role_id]
		discord_role = discord_roles_by_id.get(role_id)
		if discord_role is None:
			raise HTTPException(status_code=404, detail=f"Discord上にロール {role_id} が見つかりません")
		if discord_role.get("managed") or role_id == DISCORD_GUILD_ID:
			raise HTTPException(status_code=403, detail=f"ロール '{role_info.get('name', role_id)}' は変更できません")
		if role_id not in manageable_role_ids:
			raise HTTPException(status_code=403, detail=f"ロール '{role_info.get('name', role_id)}' はBotの権限範囲外です")

	if roles_to_add:
		role_ids_with_channel_permissions = _unwrap_discord_fetch(
			fetch_results[3], "fetch channel permission overwrites",
		)
		for role_id in roles_to_add:
			if role_id in role_ids_with_channel_permissions:
				role_name = roles_in_manifest[role_id].get("name", role_id)
				raise HTTPException(
					status_code=403,
					detail=f"ロール '{role_name}' はチャンネル権限上書きがあるため付与できません",
				)

	# --- 2. 現在のメンバーロール取得（上で並列に取得済み。取得に失敗していても、検証で拒否した場合はそちらのエラーを優先する） ---
	member_info = _unwrap_discord_fetch(member_result, "fetch member")

	if member_info is None:
		raise HTTPException(status_code=404, detail="ギルドメンバーが見つかりません。Discordサーバーに参加しているか確認してください。")

	current_role_ids: set[str] = set(member_info.get("role_ids", []))

	# --- 3. 新しいロール一覧を計算 ---
	new_role_ids = (current_role_ids | roles_to_add) - roles_to_remove

	# 実際に変化がなければスキップ
	actually_added = list(roles_to_add - current_role_ids)
	actually_removed = list(current_role_ids & roles_to_remove)
	if not actually_added and not actually_removed:
		return {"ok": True, "added": [], "removed": [], "detail": "変更点はありませんでした"}

	# --- 4. Discord 一括更新（1回の API 呼び出し）---
	try:
		await set_member_roles(DISCORD_GUILD_ID, discord_id, list(new_role_ids), token)
	except Exception as exc:
		logger.warning("Discord API call failed (update member roles)", exc_info=True)
		raise HTTPException(status_code=502, detail="Discord API error (update member roles)") from exc
	await _record_member_roles(audit, discord_id, set(actually_added), set(actually_removed))

	# --- 5. DB 一括更新 ---
	try:
		await asyncio.to_thread(
			batch_update_user_roles,
			discord_id,
			list(roles_to_add),
			list(roles_to_remove),
			audit,
		)
	except Exception as exc:
		logger.error(
			"Failed to batch update role_member_assignments in DB for user=%s: %s",
			_principal.get("sub"), exc,
		)
		# 補償トランザクション: Discord 側を元のロール一覧にロールバック
		rollback_succeeded = False
		try:
			await set_member_roles(DISCORD_GUILD_ID, discord_id, list(current_role_ids), token)
			rollback_succeeded = True
			await _record_member_roles(
				audit, discord_id, set(actually_removed), set(actually_added), ACTION_ROLLBACK,
			)
			logger.info(
				"Compensating rollback succeeded for user=%s", _principal.get("sub")
			)
		except Exception as rollback_exc:
			logger.critical(
				"Compensating rollback FAILED for user=%s: %s", _principal.get("sub"), redact_snowflakes(rollback_exc)
			)
		detail = (
			"Failed to persist role assignments to database. Discord state was reverted."
			if rollback_succeeded
			else "Failed to persist role assignments and Discord rollback failed; states may be inconsistent."
		)
		raise HTTPException(
			status_code=500,
			detail=detail,
		) from exc

	return {
		"ok": True,
		"discord_id": discord_id,
		"added": actually_added,
		"removed": actually_removed,
	}


class SelfCreateRolePayload(BaseModel):
	name: str = Field(min_length=1, max_length=100)
	color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
	category_id: str = Field(min_length=1, max_length=100)

	@field_validator("name", mode="before")
	@classmethod
	def _strip_name(cls, value: object) -> object:
		return value.strip() if isinstance(value, str) else value


# /members/sync はロール名で会員種別（admin など）を判定するため、member はこれらの名前のロールを作れない
_RESERVED_ROLE_NAME_KEYS = frozenset(
	normalize_role_name(name)
	for name in (
		*ADMIN_ROLE_NAMES, *MEMBER_ROLE_NAMES, *OBOG_ROLE_NAMES, *SUB_USER_ROLE_NAMES, PRE_MEMBER_ROLE_NAME,
	)
)


async def _rollback_created_role(role_id: str, created: dict, token: str, audit: AuditContext) -> bool:
	"""DB に保存できなかったロールを Discord から削除する。成功したら True を返す。"""
	try:
		await delete_guild_role(DISCORD_GUILD_ID, role_id, token)
	except Exception as exc:
		logger.critical("Compensating delete FAILED for created role %s: %s", role_id, redact_snowflakes(exc))
		return False
	await record_discord_audit_safely(audit, [AuditLog(
		SYSTEM_DISCORD, TARGET_ROLE, role_id, ACTION_ROLLBACK,
		{f: created.get(f) for f in DISCORD_ROLE_AUDIT_FIELDS}, None,
	)])
	return True


async def _assign_created_role(discord_id: str, role_id: str, token: str, audit: AuditContext) -> bool:
	"""作成したロールを作成者に付与する。Discord と DB の両方に反映できたら True を返す。

	DB への保存に失敗した場合は、Discord 側の付与を取り消す。
	"""
	try:
		await add_role_to_member(DISCORD_GUILD_ID, discord_id, role_id, token)
	except Exception:
		logger.warning("Discord API call failed (assign created role %s)", role_id, exc_info=True)
		return False
	await _record_member_roles(audit, discord_id, {role_id}, set())
	try:
		await asyncio.to_thread(batch_update_user_roles, discord_id, [role_id], [], audit)
	except Exception as exc:
		logger.error("Failed to save assignment of created role %s to DB (%s)", role_id, type(exc).__name__)
		try:
			await remove_role_from_member(DISCORD_GUILD_ID, discord_id, role_id, token)
			await _record_member_roles(audit, discord_id, set(), {role_id}, ACTION_ROLLBACK)
		except Exception as rollback_exc:
			logger.critical(
				"Compensating unassign FAILED for created role %s: %s", role_id, redact_snowflakes(rollback_exc)
			)
		return False
	return True


@router.post("/self-create")
async def self_create_role(
	payload: SelfCreateRolePayload,
	_principal: dict = Depends(require_member),
	audit: AuditContext = Depends(get_audit_context),
) -> dict:
	"""member が、セルフ付与できるカテゴリに Discord 権限なしのロールを作成し、自分に付与する。

	1. カテゴリ（セルフ付与と同じ条件）と、同名ロールがないことを検証する
	2. Discord にロールを作成する（permissions = 0 に固定）
	3. 実 ID でマニフェストに保存する。失敗したら Discord のロールを削除する
	4. 作成者に付与する。失敗してもロールは残し、assigned = false を返す
	"""
	audit = audit.with_operation(OP_SELF_CREATE)
	discord_id: str | None = _principal.get("discord_id")
	if not discord_id:
		raise HTTPException(status_code=400, detail="Discord ID が特定できません。Discordアカウントで再ログインしてください。")
	await enforce_rate_limit(_self_create_limiter, f"discord_id:{discord_id}", "role self create")

	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	# --- 1. 検証（DB のマニフェストを正とする） ---
	manifest = await asyncio.to_thread(fetch_manifest)
	if payload.category_id not in _self_assignable_category_ids(manifest):
		raise HTTPException(status_code=403, detail="このカテゴリにはロールを作成できません")
	name_key = normalize_role_name(payload.name)
	if name_key in _RESERVED_ROLE_NAME_KEYS:
		raise HTTPException(status_code=409, detail=f"ロール名 '{payload.name}' は予約されているため使用できません")
	if any(normalize_role_name(str(r.get("name", ""))) == name_key for r in manifest.get("roles", [])):
		raise HTTPException(status_code=409, detail=f"ロール '{payload.name}' はすでに存在します")

	role = {
		"name": payload.name,
		"color": payload.color,
		"hoist": False,
		"mentionable": True,
		"permissions": 0,
		"category_id": payload.category_id,
		"is_our_bot": False,
	}

	# --- 2. Discord に作成 ---
	try:
		created = await create_guild_role(DISCORD_GUILD_ID, token, build_role_create_payload(role))
	except Exception as exc:
		logger.warning("Discord API call failed (create role)", exc_info=True)
		raise HTTPException(status_code=502, detail="Discord API error (create role)") from exc
	role_id = created["role_id"]
	await record_discord_audit_safely(audit, [AuditLog(
		SYSTEM_DISCORD, TARGET_ROLE, role_id, ACTION_CREATE,
		None, {f: created.get(f) for f in DISCORD_ROLE_AUDIT_FIELDS},
	)])

	# --- 3. マニフェストに保存 ---
	try:
		saved = await asyncio.to_thread(insert_member_created_role, {**role, "role_id": role_id}, audit)
	except RoleNameConflictError as exc:
		# 検証後に同名のロールが作られた。作ったロールは取り消す
		await _rollback_created_role(role_id, created, token, audit)
		raise HTTPException(status_code=409, detail=f"ロール '{payload.name}' はすでに存在します") from exc
	except Exception as exc:
		logger.error("Failed to save created role %s to DB (%s)", role_id, type(exc).__name__)
		rollback_succeeded = await _rollback_created_role(role_id, created, token, audit)
		detail = (
			"Failed to persist the created role to database. Discord role was deleted."
			if rollback_succeeded
			else "Failed to persist the created role and Discord rollback failed; states may be inconsistent."
		)
		raise HTTPException(status_code=500, detail=detail) from exc

	# --- 4. 作成者に付与 ---
	assigned = await _assign_created_role(discord_id, role_id, token, audit)

	return {
		"ok": True,
		"role": {f: saved[f] for f in ("role_id", "name", "color", "permissions", "position", "category_id")},
		"assigned": assigned,
	}


@router.get("/lists")
async def get_lists(_principal: dict = Depends(require_admin)) -> dict:
	"""member_list / admin_list / pre_member_list を取得."""
	result = await asyncio.to_thread(get_member_lists)
	return result


@router.get("/debug/guilds")
async def debug_bot_guilds(_principal: dict = Depends(require_admin)) -> dict:
	"""[DEBUG] Bot が参加しているギルド一覧を取得. ギルドID設定確認用."""
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")
	
	try:
		guilds = await fetch_bot_guilds(token)
		current_guild_id = DISCORD_GUILD_ID or "NOT_SET"
		current_guild = next((g for g in guilds if g["guild_id"] == current_guild_id), None)
		
		return {
			"ok": True,
			"current_guild_id": current_guild_id,
			"current_guild": current_guild,
			"all_guilds": guilds,
			"note": "current_guild が null の場合、DISCORD_GUILD_ID 環境変数が正しくないか bot がギルドに参加していません",
		}
	except Exception as exc:
		logger.error("Debug guilds fetch failed: %s", exc)
		raise HTTPException(status_code=502, detail="Failed to fetch guilds") from exc
