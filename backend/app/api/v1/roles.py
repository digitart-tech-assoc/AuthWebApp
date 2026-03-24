"""役割: Discordロール取得API"""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Header, HTTPException

from app.db.repository import replace_roles_from_discord
from app.services.discord_client import fetch_guild_roles


router = APIRouter(prefix="/api/v1/roles", tags=["roles"])
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "1304058364560543815")


@router.post("/refresh")
async def refresh_roles_from_discord(authorization: str | None = Header(default=None)) -> dict:
	expected = f"Bearer {SHARED_SECRET}"
	if authorization != expected:
		raise HTTPException(status_code=401, detail="Unauthorized")
	if not DISCORD_TOKEN:
		raise HTTPException(status_code=500, detail="DISCORD_TOKEN is not configured")

	try:
		roles = await fetch_guild_roles(DISCORD_GUILD_ID, DISCORD_TOKEN)
	except Exception as exc:  # noqa: BLE001
		raise HTTPException(status_code=502, detail=f"Discord fetch failed: {exc}") from exc

	count = await asyncio.to_thread(replace_roles_from_discord, roles)
	return {"ok": True, "guild_id": DISCORD_GUILD_ID, "roles": count}
