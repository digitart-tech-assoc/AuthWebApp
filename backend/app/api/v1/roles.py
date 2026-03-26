"""役割: Discordロール取得API"""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import require_admin
from app.db.repository import fetch_manifest, replace_roles_from_discord, update_role_id
from app.services.discord_client import (
	build_role_create_payload,
	build_role_edit_payload,
	create_guild_role,
	delete_guild_role,
	edit_guild_role,
	fetch_guild_roles,
	reorder_guild_roles,
)


router = APIRouter(prefix="/api/v1/roles", tags=["roles"])
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")


def _get_token() -> str:
	return DISCORD_TOKEN.strip()


@router.post("/refresh")
async def refresh_roles_from_discord(_principal: dict = Depends(require_admin)) -> dict:
	token = _get_token()
	if not token:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	try:
		roles = await fetch_guild_roles(DISCORD_GUILD_ID, token)
	except Exception as exc:  # noqa: BLE001
		raise HTTPException(status_code=502, detail=f"Discord fetch failed: {exc}") from exc

	count = await asyncio.to_thread(replace_roles_from_discord, roles)
	return {"ok": True, "guild_id": DISCORD_GUILD_ID, "roles": count}


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

	actual_by_id = {role["role_id"]: role for role in actual_roles}
	desired_by_id = {role["role_id"]: role for role in desired_roles}

	updated = 0
	created = 0
	deleted = 0
	skipped_managed = 0
	errors = []

	for role in desired_roles:
		role_id = role["role_id"]
		actual = actual_by_id.get(role_id)
		if actual is None:
			try:
				new_role_discord = await create_guild_role(DISCORD_GUILD_ID, token, build_role_create_payload(role))
				created += 1
				# Replace temporary draft ID with the real Discord ID in the local DB
				if str(role_id).startswith("draft-"):
					real_id = new_role_discord["role_id"]
					await asyncio.to_thread(update_role_id, role_id, real_id)
					# Update our local mapping so the real role isn't accidentally deleted below
					desired_by_id[real_id] = role
					role["role_id"] = real_id
					actual_by_id[real_id] = new_role_discord
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
		except Exception as exc:
			msg = f"Failed to delete role {role_id}: {exc}"
			print(msg)
			errors.append(msg)

	desired_roles_sorted = sorted(desired_roles, key=lambda x: int(x.get("position", 0)))
	position_payload = []
	current_pos = 1
	for role in desired_roles_sorted:
		if role["role_id"] in actual_by_id and role["role_id"] != DISCORD_GUILD_ID:
			position_payload.append({"id": role["role_id"], "position": current_pos})
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

	return {
		"ok": len(errors) == 0,
		"guild_id": DISCORD_GUILD_ID,
		"updated": updated,
		"created": created,
		"deleted": deleted,
		"reordered": reordered,
		"skipped_managed": skipped_managed,
		"errors": errors,
	}


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


