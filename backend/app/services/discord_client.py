"""役割: Discord REST APIクライアント"""

from __future__ import annotations

import httpx


DISCORD_API_BASE = "https://discord.com/api/v10"


def _int_color_to_hex(color: int) -> str:
	return f"#{color:06x}"


async def fetch_guild_roles(guild_id: str, token: str) -> list[dict]:
	headers = {"Authorization": f"Bot {token}"}
	url = f"{DISCORD_API_BASE}/guilds/{guild_id}/roles"
	async with httpx.AsyncClient(timeout=10.0) as client:
		response = await client.get(url, headers=headers)
	response.raise_for_status()

	roles = response.json()
	return [
		{
			"role_id": role["id"],
			"name": role["name"],
			"color": _int_color_to_hex(int(role.get("color", 0))),
			"hoist": bool(role.get("hoist", False)),
			"mentionable": bool(role.get("mentionable", False)),
			"permissions": int(role.get("permissions", "0")),
			"position": int(role.get("position", 0)),
		}
		for role in roles
	]
