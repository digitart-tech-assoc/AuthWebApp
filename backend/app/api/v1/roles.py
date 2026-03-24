"""役割: Discordロール取得API"""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Header, HTTPException

from app.db.repository import fetch_manifest, replace_roles_from_discord
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
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "1304058364560543815")


def _get_token() -> str:
	return DISCORD_TOKEN.strip()


@router.post("/refresh")
async def refresh_roles_from_discord(authorization: str | None = Header(default=None)) -> dict:
	expected = f"Bearer {SHARED_SECRET}"
	if authorization != expected:
		raise HTTPException(status_code=401, detail="Unauthorized")
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
async def push_roles_to_discord(authorization: str | None = Header(default=None)) -> dict:
	expected = f"Bearer {SHARED_SECRET}"
	if authorization != expected:
		raise HTTPException(status_code=401, detail="Unauthorized")
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

	for role in desired_roles:
		role_id = role["role_id"]
		actual = actual_by_id.get(role_id)
		if actual is None:
			try:
				await create_guild_role(DISCORD_GUILD_ID, token, build_role_create_payload(role))
				created += 1
			except Exception:
				# DB role_id を保持する都合上、作成結果の role_id 再マッピングは現時点では行わない。
				pass
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
		except Exception:
			pass

	for role in actual_roles:
		role_id = role["role_id"]
		if role_id in desired_by_id:
			continue
		if role.get("managed") or role_id == DISCORD_GUILD_ID:
			continue
		try:
			await delete_guild_role(DISCORD_GUILD_ID, role_id, token)
			deleted += 1
		except Exception:
			pass

	position_payload = [
		{"id": role["role_id"], "position": int(role.get("position", 0))}
		for role in sorted(desired_roles, key=lambda x: int(x.get("position", 0)))
		if role["role_id"] in actual_by_id and role["role_id"] != DISCORD_GUILD_ID
	]
	reordered = 0
	if position_payload:
		try:
			await reorder_guild_roles(DISCORD_GUILD_ID, token, position_payload)
			reordered = len(position_payload)
		except Exception:
			reordered = 0

	return {
		"ok": True,
		"guild_id": DISCORD_GUILD_ID,
		"updated": updated,
		"created": created,
		"deleted": deleted,
		"reordered": reordered,
		"skipped_managed": skipped_managed,
	}
