"""役割: Discord REST APIクライアント"""

from __future__ import annotations

import httpx


DISCORD_API_BASE = "https://discord.com/api/v10"


def _int_color_to_hex(color: int) -> str:
	return f"#{color:06x}"


def _hex_color_to_int(color: str) -> int:
	value = color.strip()
	if value.startswith("#"):
		value = value[1:]
	if not value:
		return 0
	return int(value, 16)


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
			"managed": bool(role.get("managed", False)),
		}
		for role in roles
	]


def _headers(token: str) -> dict[str, str]:
	return {
		"Authorization": f"Bot {token}",
		"Content-Type": "application/json",
	}


async def edit_guild_role(guild_id: str, role_id: str, token: str, payload: dict) -> None:
	url = f"{DISCORD_API_BASE}/guilds/{guild_id}/roles/{role_id}"
	async with httpx.AsyncClient(timeout=10.0) as client:
		response = await client.patch(url, headers=_headers(token), json=payload)
	response.raise_for_status()


async def create_guild_role(guild_id: str, token: str, payload: dict) -> dict:
	url = f"{DISCORD_API_BASE}/guilds/{guild_id}/roles"
	async with httpx.AsyncClient(timeout=10.0) as client:
		response = await client.post(url, headers=_headers(token), json=payload)
	response.raise_for_status()
	role = response.json()
	return {
		"role_id": role["id"],
		"name": role["name"],
		"position": int(role.get("position", 0)),
	}


async def delete_guild_role(guild_id: str, role_id: str, token: str) -> None:
	url = f"{DISCORD_API_BASE}/guilds/{guild_id}/roles/{role_id}"
	async with httpx.AsyncClient(timeout=10.0) as client:
		response = await client.delete(url, headers=_headers(token))
	response.raise_for_status()


async def reorder_guild_roles(guild_id: str, token: str, positions: list[dict]) -> None:
	url = f"{DISCORD_API_BASE}/guilds/{guild_id}/roles"
	async with httpx.AsyncClient(timeout=10.0) as client:
		response = await client.patch(url, headers=_headers(token), json=positions)
	response.raise_for_status()


def build_role_edit_payload(desired: dict, actual: dict) -> dict:
	payload: dict = {}
	if desired.get("name") != actual.get("name"):
		payload["name"] = desired.get("name")
	if desired.get("hoist", False) != actual.get("hoist", False):
		payload["hoist"] = desired.get("hoist", False)
	if desired.get("mentionable", False) != actual.get("mentionable", False):
		payload["mentionable"] = desired.get("mentionable", False)
	desired_permissions = int(desired.get("permissions", 0))
	if desired_permissions != int(actual.get("permissions", 0)):
		payload["permissions"] = str(desired_permissions)
	desired_color = _hex_color_to_int(str(desired.get("color", "#000000")))
	actual_color = _hex_color_to_int(str(actual.get("color", "#000000")))
	if desired_color != actual_color:
		payload["color"] = desired_color
	return payload


def build_role_create_payload(desired: dict) -> dict:
	return {
		"name": desired.get("name"),
		"hoist": desired.get("hoist", False),
		"mentionable": desired.get("mentionable", False),
		"permissions": str(int(desired.get("permissions", 0))),
		"color": _hex_color_to_int(str(desired.get("color", "#000000"))),
	}
