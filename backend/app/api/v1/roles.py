"""役割: Discordロール取得API"""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel

from app.core.auth import require_admin, require_member
from app.db.repository import (
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
	fetch_guild_members_with_role,
	fetch_guild_roles,
	remove_role_from_member,
	reorder_guild_roles,
)


router = APIRouter(prefix="/api/v1/roles", tags=["roles"])
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")


def _get_token() -> str:
	return DISCORD_TOKEN.strip()


@router.post("/refresh")
async def refresh_roles_from_discord(_principal: dict = Depends(require_member)) -> dict:
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	try:
		print("[DEBUG] Starting Discord roles refresh...")
		roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
		print(f"[DEBUG] Fetched {len(roles)} roles from Discord")
	except Exception as exc:
		error_detail = str(exc)
		print(f"[ERROR] Discord roles fetch failed: {error_detail}")
		import traceback
		traceback.print_exc()
		raise HTTPException(status_code=502, detail=f"Discord API error: {error_detail}") from exc

	try:
		count = await asyncio.to_thread(replace_roles_from_discord, roles)
		print(f"[DEBUG] Replaced {count} roles in database")
	except Exception as exc:
		error_detail = str(exc)
		print(f"[ERROR] Database replace_roles failed: {error_detail}")
		import traceback
		traceback.print_exc()
		raise HTTPException(status_code=502, detail=f"Database error: {error_detail}") from exc

	# Also fetch all guild members and their role assignments
	members = []
	try:
		members = await fetch_all_guild_members(DISCORD_GUILD_ID, token)
		print(f"[DEBUG] Fetched {len(members)} guild members")
		await asyncio.to_thread(save_guild_members, [
			{"user_id": m["user_id"], "username": m["username"],
			 "display_name": m["display_name"], "avatar": m["avatar"]}
			for m in members
		])
		print(f"[DEBUG] Saved {len(members)} guild members to database")
		# Build role_id -> [user_id] mapping from member data
		assignments: dict[str, list[str]] = {}
		for m in members:
			for role_id in m.get("role_ids", []):
				assignments.setdefault(role_id, []).append(m["user_id"])
		print(f"[DEBUG] Found {len(assignments)} roles with assignments. Saving to DB...")
		# First clear ALL existing assignments so that roles with 0 members don't linger
		await asyncio.to_thread(clear_all_role_assignments)
		await asyncio.to_thread(save_role_assignments, assignments)
		print(f"[DEBUG] Saved role assignments to DB")
	except Exception as exc:
		error_detail = str(exc)
		print(f"[ERROR] Failed to fetch or map guild members: {error_detail}")
		import traceback
		traceback.print_exc()
		# Don't fail the entire request if member sync fails
		print(f"[WARNING] Continuing without member sync")

	return {"ok": True, "guild_id": DISCORD_GUILD_ID, "roles": count, "members": len(members)}


@router.post("/push")
async def push_roles_to_discord(_principal: dict = Depends(require_member)) -> dict:
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	manifest = await asyncio.to_thread(fetch_manifest)
	desired_roles = manifest.get("roles", [])

	try:
		actual_roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
	except Exception as exc:  # noqa: BLE001
		raise HTTPException(status_code=502, detail=f"Discord fetch failed: {exc}") from exc

	actual_by_id = {role["role_id"]: role for role in actual_roles}
	desired_by_id = {role["role_id"]: role for role in desired_roles}

	updated = 0
	created = 0
	deleted = 0
	skipped_managed = 0
	errors = []
	created_real_ids: set[str] = set()  # track real Discord IDs for newly created roles
	deleted_role_ids: set[str] = set()  # track deleted roles to skip member sync

	for role in desired_roles:
		role_id = role["role_id"]
		actual = actual_by_id.get(role_id)
		if actual is None:
			try:
				new_role_discord = await create_guild_role(DISCORD_GUILD_ID, token, build_role_create_payload(role))
				created += 1
				real_id = new_role_discord["role_id"]
				# Replace temporary draft ID with the real Discord ID in the local DB
				if str(role_id).startswith("draft-"):
					await asyncio.to_thread(update_role_id, role_id, real_id)
					# Update our local mapping so the real role isn't accidentally deleted below
					desired_by_id[real_id] = role
					role["role_id"] = real_id
					actual_by_id[real_id] = new_role_discord
					created_real_ids.add(real_id)
			except Exception as exc:
				msg = f"Failed to create role locally {role_id}: {exc}"
				print(msg)
				errors.append(msg)
				import traceback
				traceback.print_exc()
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
			print(msg)
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
			print(msg)
			errors.append(msg)

	# Build position payload: sort all desired roles by their position value (ascending = lower priority).
	# Assign contiguous 1..N positions so Discord gets a clean, gapless ordering.
	# Include roles that were just created (created_real_ids) since their real IDs are now in actual_by_id.
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
			print(msg)
			errors.append(msg)
			reordered = 0

	# Apply role assignment diffs: compare DB desired assignments vs current Discord member roles
	assigned_adds = 0
	assigned_removes = 0
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
					# Ignore 404 (user not in guild) similarly to reconcile behavior
					if e.response is not None and e.response.status_code == 404:
						continue
					errors.append(f"Failed to add role {role_id} to {user_id}: {e}")
				except Exception as exc:
					errors.append(f"Failed to add role {role_id} to {user_id}: {exc}")
			for user_id in current_set - desired_set:
				try:
					await remove_role_from_member(DISCORD_GUILD_ID, user_id, role_id, token)
					assigned_removes += 1
				except httpx.HTTPStatusError as e:
					# Ignore 404 (user not in guild)
					if e.response is not None and e.response.status_code == 404:
						continue
					errors.append(f"Failed to remove role {role_id} from {user_id}: {e}")
				except Exception as exc:
					errors.append(f"Failed to remove role {role_id} from {user_id}: {exc}")

		# Also handle roles that exist in Discord but have been completely removed from desired_assignments
		# (fetch_role_assignments only returns role_ids with at least 1 member, so 0-member roles are missing)
		for role_id, current_users in current_by_role.items():
			if role_id in desired_assignments:
				continue  # already handled above
			if role_id == DISCORD_GUILD_ID or role_id.startswith("draft-"):
				continue
			if role_id not in actual_by_id and role_id not in created_real_ids:
				continue
			if role_id in deleted_role_ids:
				continue
			# This role has Discord members but no desired members → remove all
			for user_id in current_users:
				try:
					await remove_role_from_member(DISCORD_GUILD_ID, user_id, role_id, token)
					assigned_removes += 1
				except httpx.HTTPStatusError as e:
					# Ignore 404 (user not in guild)
					if e.response is not None and e.response.status_code == 404:
						continue
					errors.append(f"Failed to remove role {role_id} from {user_id}: {e}")
				except Exception as exc:
					errors.append(f"Failed to remove role {role_id} from {user_id}: {exc}")
	except Exception as exc:
		errors.append(f"Failed to apply assignment diffs: {exc}")

	return {
		"ok": len(errors) == 0,
		"guild_id": DISCORD_GUILD_ID,
		"updated": updated,
		"created": created,
		"deleted": deleted,
		"reordered": reordered,
		"skipped_managed": skipped_managed,
		"assigned_adds": assigned_adds,
		"assigned_removes": assigned_removes,
		"errors": errors,
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


@router.post("/members/sync")
async def sync_members_from_discord(_principal: dict = Depends(require_admin)) -> dict:
	"""Discord ギルドメンバーから member_list / admin_list / pre_member_list を同期."""
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	try:
		print(f"[DEBUG] sync_members: GUILD_ID={DISCORD_GUILD_ID}")
		
		# Get all roles from Discord
		roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
		print(f"[DEBUG] Fetched {len(roles)} roles from Discord")
		for r in roles:
			print(f"[DEBUG]   Role: {r['name']} (id={r['role_id']})")
		
		# Identify role IDs by name pattern (configurable from env)
		# Expected roles: "member", "OBOG", "administrator", "pre-member"
		member_role_names = {"member", "会員", "Member"}
		obog_role_names = {"OBOG", "OB/OG", "OB-OG"}
		admin_role_names = {"administrator", "管理者", "Administrator"}
		pre_member_role_name = "pre-member"
		
		member_role_ids = [r["role_id"] for r in roles if r["name"] in member_role_names]
		obog_role_ids = [r["role_id"] for r in roles if r["name"] in obog_role_names]
		admin_role_ids = [r["role_id"] for r in roles if r["name"] in admin_role_names]
		pre_member_role_id = next((r["role_id"] for r in roles if r["name"] == pre_member_role_name), None)
		
		print(f"[DEBUG] Matched roles:")
		print(f"[DEBUG]   member_role_ids={member_role_ids}")
		print(f"[DEBUG]   obog_role_ids={obog_role_ids}")
		print(f"[DEBUG]   admin_role_ids={admin_role_ids}")
		print(f"[DEBUG]   pre_member_role_id={pre_member_role_id}")
		
		# Fetch members for each role
		members_data = {}
		for role_id in member_role_ids + obog_role_ids + admin_role_ids + ([pre_member_role_id] if pre_member_role_id else []):
			if role_id:
				members = await fetch_guild_members_with_role(DISCORD_GUILD_ID, role_id, token)
				print(f"[DEBUG] Fetched {len(members)} members for role {role_id}")
				members_data[role_id] = members
		
		# Sync to DB
		print(f"[DEBUG] Syncing to DB with members_data keys: {list(members_data.keys())}")
		result = await asyncio.to_thread(
			sync_member_lists,
			member_role_ids,
			obog_role_ids,
			admin_role_ids,
			pre_member_role_id,
			members_data
		)
		print(f"[DEBUG] Sync result: {result}")
		
		return {
			"ok": True,
			"guild_id": DISCORD_GUILD_ID,
			"member_list": result["member_list"],
			"admin_list": result["admin_list"],
			"pre_member_list": result["pre_member_list"],
		}
	except Exception as exc:  # noqa: BLE001
		import traceback
		print(f"[ERROR] Discord sync failed: {exc}")
		traceback.print_exc()
		raise HTTPException(status_code=502, detail=f"Discord sync failed: {exc}") from exc


class SelfAssignPayload(BaseModel):
	role_id: str


# カテゴリ名で付与を禁止するカテゴリ（バックエンド側でも確認）
MEMBER_RESTRICTED_CATEGORY_NAMES = {"会員情報", "学部学科", "学年"}


@router.post("/self-assign")
async def self_assign_role(
	payload: SelfAssignPayload,
	_principal: dict = Depends(require_member),
) -> dict:
	"""memberが自分自身にロールを付与する。禁止カテゴリに属するロールは拒否。"""
	discord_id: str | None = _principal.get("discord_id")
	if not discord_id:
		raise HTTPException(status_code=400, detail="Discord ID が特定できません。Discordアカウントで再ログインしてください。")

	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	# マニフェストで禁止カテゴリチェック
	manifest = await asyncio.to_thread(fetch_manifest)
	restricted_cat_ids = {
		c["id"] for c in manifest.get("categories", [])
		if c["name"] in MEMBER_RESTRICTED_CATEGORY_NAMES
	}
	role_info = next((r for r in manifest.get("roles", []) if r["role_id"] == payload.role_id), None)
	if role_info and role_info.get("category_id") in restricted_cat_ids:
		raise HTTPException(status_code=403, detail="このロールは付与できません（禁止カテゴリ）")

	try:
		await add_role_to_member(DISCORD_GUILD_ID, discord_id, payload.role_id, token)
	except Exception as exc:
		raise HTTPException(status_code=502, detail=f"Discord API error: {exc}") from exc

	# DB のロール割り当ても更新
	try:
		assignments = await asyncio.to_thread(fetch_role_assignments)
		current = set(assignments.get(payload.role_id, []))
		current.add(discord_id)
		await asyncio.to_thread(save_role_assignments, {payload.role_id: list(current)})
	except Exception:
		pass  # DB更新失敗は無視（Discord側には反映済み）

	return {"ok": True, "role_id": payload.role_id, "discord_id": discord_id}


@router.get("/lists")
async def get_lists(_principal: dict = Depends(require_member)) -> dict:
	"""member_list / admin_list / pre_member_list を取得."""
	result = await asyncio.to_thread(get_member_lists)
	return result


@router.get("/debug/guilds")
async def debug_bot_guilds() -> dict:
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
		print(f"[ERROR] Debug guilds fetch failed: {error_detail}")
		raise HTTPException(status_code=502, detail=f"Failed to fetch guilds: {error_detail}") from exc
