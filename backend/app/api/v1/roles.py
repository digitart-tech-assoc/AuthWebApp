"""役割: Discordロール取得API"""
from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from app.core.auth import require_admin, require_member
from app.core.config import (
	ADMIN_ROLE_NAMES,
	MEMBER_RESTRICTED_CATEGORY_NAMES,
	MEMBER_ROLE_NAMES,
	OBOG_ROLE_NAMES,
	PRE_MEMBER_ROLE_NAME,
)
from app.db.repository import (
	batch_update_user_roles,
	clear_all_role_assignments,
	fetch_guild_members,
	fetch_manifest,
	fetch_role_assignments,
	get_member_lists,
	replace_roles_from_discord,
	save_guild_members,
	save_role_assignments,
	sync_member_lists,
	update_role_id,
)
from app.services.discord_client import (
	add_role_to_member,
	build_role_create_payload,
	build_role_edit_payload,
	create_guild_role,
	delete_guild_role,
	edit_guild_role,
	fetch_all_guild_members,
	fetch_bot_guilds,
	fetch_guild_member,
	fetch_guild_members_with_role,
	fetch_guild_roles,
	remove_role_from_member,
	reorder_guild_roles,
	set_member_roles,
)


router = APIRouter(prefix="/api/v1/roles", tags=["roles"])
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
DISCORD_BOT_URL = os.getenv("DISCORD_BOT_URL", "http://discord-bot:8000")
SHARED_SECRET = os.getenv("SHARED_SECRET", "")


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
				logger.info("Bot reconcile triggered successfully: %s", resp.json())
				return True
			else:
				logger.warning("Bot reconcile failed with status %d: %s", resp.status_code, resp.text)
				return False
	except Exception as e:
		logger.warning("Failed to trigger bot reconcile: %s", e)
		return False


@router.post("/refresh")
async def refresh_roles_from_discord(_principal: dict = Depends(require_member)) -> dict:
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	try:
		logger.debug("Starting Discord roles refresh...")
		roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
		logger.debug("Fetched %d roles from Discord", len(roles))
	except Exception as exc:
		error_detail = str(exc)
		logger.exception("Discord roles fetch failed: %s", error_detail)
		raise HTTPException(status_code=502, detail=f"Discord API error: {error_detail}") from exc

	try:
		count = await asyncio.to_thread(replace_roles_from_discord, roles)
		logger.debug("Replaced %d roles in database", count)
	except Exception as exc:
		error_detail = str(exc)
		logger.exception("Database replace_roles failed: %s", error_detail)
		raise HTTPException(status_code=502, detail=f"Database error: {error_detail}") from exc

	# Also fetch all guild members and their role assignments
	members = []
	try:
		members = await fetch_all_guild_members(DISCORD_GUILD_ID, token)
		logger.debug("Fetched %d guild members", len(members))
		await asyncio.to_thread(save_guild_members, [
			{"user_id": m["user_id"], "username": m["username"],
			 "display_name": m["display_name"], "avatar": m["avatar"]}
			for m in members
		])
		logger.debug("Saved %d guild members to database", len(members))
		# Build role_id -> [user_id] mapping from member data
		assignments: dict[str, list[str]] = {}
		for m in members:
			for role_id in m.get("role_ids", []):
				assignments.setdefault(role_id, []).append(m["user_id"])
		logger.debug("Found %d roles with assignments, total members: %d", len(assignments), sum(len(u) for u in assignments.values()))
		# First clear ALL existing assignments so that roles with 0 members don't linger
		logger.debug("Clearing all existing role assignments...")
		await asyncio.to_thread(clear_all_role_assignments)
		logger.debug("Saving new role assignments...")
		await asyncio.to_thread(save_role_assignments, assignments)
		logger.debug("Role assignments saved successfully")
	except Exception as exc:
		error_detail = str(exc)
		logger.exception("Failed to fetch or map guild members: %s", error_detail)
		# Don't fail the entire request if member sync fails
		logger.warning("Continuing without member sync")

	return {"ok": True, "guild_id": DISCORD_GUILD_ID, "roles": count, "members": len(members)}


async def _sync_role_definitions(
	desired_roles: list[dict],
	actual_roles: list[dict],
	token: str,
) -> tuple[int, int, int, int, set[str], set[str], list[str], dict, dict]:
	"""ロール定義の同期（Create / Update / Delete）"""
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
				if str(role_id).startswith("draft-"):
					await asyncio.to_thread(update_role_id, role_id, real_id)
					desired_by_id[real_id] = role
					role["role_id"] = real_id
					actual_by_id[real_id] = new_role_discord
					created_real_ids.add(real_id)
			except Exception as exc:
				msg = f"Failed to create role locally {role_id}: {exc}"
				logger.exception("%s", msg)
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
		except Exception as exc:
			msg = f"Failed to update role in discord {role_id}: {exc}"
			logger.error("%s", msg)
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
		except Exception as exc:
			msg = f"Failed to delete role {role_id}: {exc}"
			logger.error("%s", msg)
			errors.append(msg)

	return (
		updated, created, deleted, skipped_managed,
		created_real_ids, deleted_role_ids, errors,
		actual_by_id, desired_by_id
	)


async def _reorder_roles(
	desired_roles: list[dict],
	actual_by_id: dict,
	created_real_ids: set[str],
	token: str,
) -> tuple[int, list[str]]:
	"""ロール順序の再編成（contiguous 1..N positions）"""
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
			reordered = len(position_payload)
		except Exception as exc:
			msg = f"Failed to reorder roles: {exc}"
			logger.error("%s", msg)
			errors.append(msg)
			reordered = 0
	return reordered, errors


async def _apply_role_assignment_diffs(
	actual_by_id: dict,
	created_real_ids: set[str],
	deleted_role_ids: set[str],
	token: str,
) -> tuple[int, int, list[str]]:
	"""メンバーロール割り当ての差分適用"""
	assigned_adds = 0
	assigned_removes = 0
	errors: list[str] = []

	try:
		desired_assignments = await asyncio.to_thread(fetch_role_assignments)
		current_members = await fetch_all_guild_members(DISCORD_GUILD_ID, token)
		current_by_role: dict[str, set[str]] = {}
		for m in current_members:
			for rid in m.get("role_ids", []):
				current_by_role.setdefault(rid, set()).add(m["user_id"])

		for role_id, desired_users in desired_assignments.items():
			if role_id == DISCORD_GUILD_ID or role_id.startswith("draft-"):
				continue
			if role_id not in actual_by_id and role_id not in created_real_ids:
				continue
			desired_set = set(desired_users)
			current_set = current_by_role.get(role_id, set())
			for user_id in desired_set - current_set:
				try:
					await add_role_to_member(DISCORD_GUILD_ID, user_id, role_id, token)
					assigned_adds += 1
				except httpx.HTTPStatusError as e:
					if e.response is not None and e.response.status_code in (404, 403):
						logger.warning("Skipped add role %s to %s: HTTP %s", role_id, user_id, e.response.status_code)
						continue
					errors.append(f"Failed to add role {role_id} to {user_id}: {e}")
				except Exception as exc:
					errors.append(f"Failed to add role {role_id} to {user_id}: {exc}")
			for user_id in current_set - desired_set:
				try:
					await remove_role_from_member(DISCORD_GUILD_ID, user_id, role_id, token)
					assigned_removes += 1
				except httpx.HTTPStatusError as e:
					if e.response is not None and e.response.status_code in (404, 403):
						logger.warning("Skipped remove role %s from %s: HTTP %s", role_id, user_id, e.response.status_code)
						continue
					errors.append(f"Failed to remove role {role_id} from {user_id}: {e}")
				except Exception as exc:
					errors.append(f"Failed to remove role {role_id} from {user_id}: {exc}")

		for role_id, current_users in current_by_role.items():
			if role_id in desired_assignments:
				continue
			if role_id == DISCORD_GUILD_ID or role_id.startswith("draft-"):
				continue
			if role_id not in actual_by_id and role_id not in created_real_ids:
				continue
			if role_id in deleted_role_ids:
				continue
			for user_id in current_users:
				try:
					await remove_role_from_member(DISCORD_GUILD_ID, user_id, role_id, token)
					assigned_removes += 1
				except httpx.HTTPStatusError as e:
					if e.response is not None and e.response.status_code in (404, 403):
						logger.warning("Skipped remove role %s from %s: HTTP %s", role_id, user_id, e.response.status_code)
						continue
					errors.append(f"Failed to remove role {role_id} from {user_id}: {e}")
				except Exception as exc:
					errors.append(f"Failed to remove role {role_id} from {user_id}: {exc}")
	except Exception as exc:
		errors.append(f"Failed to apply assignment diffs: {exc}")

	return assigned_adds, assigned_removes, errors


@router.post("/push")
async def push_roles_to_discord(_principal: dict = Depends(require_admin)) -> dict:
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	manifest = await asyncio.to_thread(fetch_manifest)
	desired_roles = manifest.get("roles", [])

	try:
		actual_roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
	except Exception as exc:  # noqa: BLE001
		raise HTTPException(status_code=502, detail=f"Discord fetch failed: {exc}") from exc

	(
		updated, created, deleted, skipped_managed,
		created_real_ids, deleted_role_ids, sync_errors,
		actual_by_id, desired_by_id
	) = await _sync_role_definitions(desired_roles, actual_roles, token)

	reordered, reorder_errors = await _reorder_roles(
		desired_roles, actual_by_id, created_real_ids, token
	)

	assigned_adds, assigned_removes, assign_errors = await _apply_role_assignment_diffs(
		actual_by_id, created_real_ids, deleted_role_ids, token
	)

	all_errors = sync_errors + reorder_errors + assign_errors

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
		"bot_reconciled": bot_reconciled,
		"errors": all_errors,
	}


@router.get("/members")
async def get_role_members(_principal: dict = Depends(require_member)) -> dict:
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
		raise HTTPException(status_code=502, detail=f"Discord update failed: {exc}") from exc

	return {"ok": True, "role_id": role_id, "permissions": payload.permissions}


def _match_role_ids(roles: list[dict]) -> dict[str, Any]:
	"""Discordロール一覧から期待されるロール種別のIDを特定する"""
	member_role_ids = [r["role_id"] for r in roles if r["name"] in MEMBER_ROLE_NAMES]
	obog_role_ids = [r["role_id"] for r in roles if r["name"] in OBOG_ROLE_NAMES]
	admin_role_ids = [r["role_id"] for r in roles if r["name"] in ADMIN_ROLE_NAMES]
	pre_member_role_id = next((r["role_id"] for r in roles if r["name"] == PRE_MEMBER_ROLE_NAME), None)

	all_matched = member_role_ids + obog_role_ids + admin_role_ids
	if pre_member_role_id:
		all_matched.append(pre_member_role_id)

	return {
		"member_role_ids": member_role_ids,
		"obog_role_ids": obog_role_ids,
		"admin_role_ids": admin_role_ids,
		"pre_member_role_id": pre_member_role_id,
		"all_matched_role_ids": all_matched,
	}


@router.post("/members/sync")
async def sync_members_from_discord(_principal: dict = Depends(require_admin)) -> dict:
	"""Discord ギルドメンバーから member_list / admin_list / pre_member_list を同期."""
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
		all_matched_role_ids = matched["all_matched_role_ids"]
		
		logger.debug("Matched roles:")
		logger.debug("  member_role_ids=%s", member_role_ids)
		logger.debug("  obog_role_ids=%s", obog_role_ids)
		logger.debug("  admin_role_ids=%s", admin_role_ids)
		logger.debug("  pre_member_role_id=%s", pre_member_role_id)
		
		if not all_matched_role_ids:
			available_names = [r["name"] for r in roles]
			error_detail = (
				f"Failed to match Discord role names to expected roles. "
				f"Expected to find at least one of: member/会員/Member, OBOG/OB/OG/OB-OG, "
				f"administrator/管理者, pre-member. "
				f"Available Discord role names: {available_names}"
			)
			logger.error("%s", error_detail)
			raise HTTPException(status_code=400, detail=error_detail)
		
		# Fetch members for each role
		members_data = {}
		all_unique_members = {}
		for role_id in member_role_ids + obog_role_ids + admin_role_ids + ([pre_member_role_id] if pre_member_role_id else []):
			if role_id:
				members = await fetch_guild_members_with_role(DISCORD_GUILD_ID, role_id, token)
				logger.debug("Fetched %d members for role %s", len(members), role_id)
				members_data[role_id] = members
				for m in members:
					all_unique_members[m["user_id"]] = m
		
		logger.debug("Saving %d unique guild members metadata", len(all_unique_members))
		await asyncio.to_thread(save_guild_members, list(all_unique_members.values()))
		
		# Sync to DB
		logger.debug("Syncing role memberships to DB with members_data keys: %s", list(members_data.keys()))
		result = await asyncio.to_thread(
			sync_member_lists,
			member_role_ids,
			obog_role_ids,
			admin_role_ids,
			pre_member_role_id,
			members_data
		)
		logger.debug("Sync result: %s", result)
		
		return {
			"ok": True,
			"guild_id": DISCORD_GUILD_ID,
			"member_list": result["member_list"],
			"admin_list": result["admin_list"],
			"pre_member_list": result["pre_member_list"],
		}
	except Exception as exc:  # noqa: BLE001
		logger.exception("Discord sync failed: %s", exc)
		raise HTTPException(status_code=502, detail=f"Discord sync failed: {exc}") from exc


class SelfBatchPayload(BaseModel):
	roles_to_add: list[str] = Field(default_factory=list, max_length=50)
	roles_to_remove: list[str] = Field(default_factory=list, max_length=50)


@router.post("/self-batch")
async def self_batch_roles(
	payload: SelfBatchPayload,
	_principal: dict = Depends(require_member),
) -> dict:
	"""memberが自分自身のロールを一括で付与・解除する。

	1. 全ロールを一括バリデーション（禁止カテゴリ）
	2. 現在の Discord ロール一覧を取得
	3. Discord の PATCH /members/{user_id} で1回の API 呼び出しで一括更新
	4. DB を一括更新
	5. Discord 更新後に DB 更新が失敗した場合はロールバック
	"""
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

	# --- 1. 一括バリデーション ---
	manifest = await asyncio.to_thread(fetch_manifest)
	roles_in_manifest = {r["role_id"]: r for r in manifest.get("roles", [])}
	restricted_cat_ids = {
		c["id"] for c in manifest.get("categories", [])
		if c["name"] in MEMBER_RESTRICTED_CATEGORY_NAMES or c.get("is_restricted", False)
	}

	for role_id in all_role_ids:
		role_info = roles_in_manifest.get(role_id)
		if role_info is None:
			raise HTTPException(status_code=404, detail=f"指定されたロール {role_id} が見つかりません")
		if role_info.get("category_id") in restricted_cat_ids:
			raise HTTPException(
				status_code=403,
				detail=f"ロール '{role_info.get('name', role_id)}' は変更できません（禁止カテゴリ）",
			)

	# UIの表示制約に依存せず、Discord側のロール階層とmanagedフラグもAPIで検証する。
	try:
		discord_roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
	except Exception as exc:
		raise HTTPException(status_code=502, detail=f"Discord API error (fetch roles): {exc}") from exc

	discord_roles_by_id = {role["role_id"]: role for role in discord_roles}
	bot_role = next((role for role in discord_roles if role.get("is_our_bot")), None)
	for role_id in all_role_ids:
		role_info = roles_in_manifest[role_id]
		discord_role = discord_roles_by_id.get(role_id)
		if discord_role is None:
			raise HTTPException(status_code=404, detail=f"Discord上にロール {role_id} が見つかりません")
		if discord_role.get("managed") or role_id == DISCORD_GUILD_ID:
			raise HTTPException(status_code=403, detail=f"ロール '{role_info.get('name', role_id)}' は変更できません")
		if bot_role and discord_role.get("position", 0) >= bot_role.get("position", 0):
			raise HTTPException(status_code=403, detail=f"ロール '{role_info.get('name', role_id)}' はBotの権限範囲外です")

	# --- 2. 現在のメンバーロール取得 ---
	try:
		member_info = await fetch_guild_member(DISCORD_GUILD_ID, discord_id, token)
	except Exception as exc:
		raise HTTPException(status_code=502, detail=f"Discord API error (fetch member): {exc}") from exc

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
		raise HTTPException(status_code=502, detail=f"Discord API error: {exc}") from exc

	# --- 5. DB 一括更新 ---
	try:
		await asyncio.to_thread(
			batch_update_user_roles,
			discord_id,
			list(roles_to_add),
			list(roles_to_remove),
		)
	except Exception as exc:
		logger.error(
			"Failed to batch update role_member_assignments in DB for user_id=%s: %s",
			discord_id, exc,
		)
		# 補償トランザクション: Discord 側を元のロール一覧にロールバック
		rollback_succeeded = False
		try:
			await set_member_roles(DISCORD_GUILD_ID, discord_id, list(current_role_ids), token)
			rollback_succeeded = True
			logger.info(
				"Compensating rollback succeeded for discord_id=%s", discord_id
			)
		except Exception as rollback_exc:
			logger.critical(
				"Compensating rollback FAILED for discord_id=%s: %s", discord_id, rollback_exc
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


@router.get("/lists")
async def get_lists(_principal: dict = Depends(require_member)) -> dict:
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
		error_detail = str(exc)
		logger.error("Debug guilds fetch failed: %s", error_detail)
		raise HTTPException(status_code=502, detail=f"Failed to fetch guilds: {error_detail}") from exc
