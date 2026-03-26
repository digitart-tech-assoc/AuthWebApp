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
		# Get the bot's own user ID to identify our bot role
		me_resp = await client.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
		me_resp.raise_for_status()
		bot_id = me_resp.json()["id"]

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
			"is_our_bot": (role.get("tags") or {}).get("bot_id") == bot_id,
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


async def fetch_guild_members_with_role(guild_id: str, role_id: str, token: str) -> list[dict]:
	"""ギルド内の特定のロールを持つメンバーを取得"""
	headers = {"Authorization": f"Bot {token}"}
	url = f"{DISCORD_API_BASE}/guilds/{guild_id}/members"
	
	members = []
	after = "0"
	total_checked = 0
	
	try:
		async with httpx.AsyncClient(timeout=30.0) as client:
			while True:
				params = {"limit": 1000, "after": after}
				response = await client.get(url, headers=headers, params=params)
				response.raise_for_status()
				
				batch = response.json()
				print(f"[DEBUG] fetch_members: role_id={role_id} (type={type(role_id).__name__}), batch size={len(batch)}")
				if not batch:
					break
				
				total_checked += len(batch)
				# ロールを持つメンバーをフィルタ
				for i, member in enumerate(batch):
					member_roles = member.get("roles", [])
					# Debug: first member only
					if i == 0:
						print(f"[DEBUG]   first member roles: {member_roles} (types: {[type(r).__name__ for r in member_roles]})")
						print(f"[DEBUG]   checking if {role_id} in {member_roles}")
					
					if str(role_id) in [str(r) for r in member_roles]:
						members.append({
							"user_id": member["user"]["id"],
							"username": member["user"]["username"],
							"discriminator": member["user"].get("discriminator", "0"),
							"display_name": member.get("nick") or member["user"]["username"],
						})
				
				print(f"[DEBUG] fetch_members: found {len(members)} total so far (checked {total_checked})")
				after = batch[-1]["user"]["id"]
	except Exception as e:
		print(f"[ERROR] fetch_guild_members_with_role failed: {e}")
		import traceback
		traceback.print_exc()
	
	print(f"[DEBUG] fetch_members: role_id={role_id} final count={len(members)}")
	return members


async def create_channel_invite(channel_id: str, token: str, max_uses: int = 1, max_age_seconds: int = 604800, unique: bool = True) -> dict:
	"""Create a Discord invite for a specific channel.

	Args:
		channel_id: Channel Snowflake ID
		token: Bot token
		max_uses: Maximum number of uses (1 => single-use)
		max_age_seconds: Expiration in seconds (604800 = 7 days)
		unique: Whether to create a unique invite even if similar exists

	Returns:
		Invite payload as returned by Discord API.
	"""
	url = f"{DISCORD_API_BASE}/channels/{channel_id}/invites"
	payload = {
		"max_uses": int(max_uses),
		"max_age": int(max_age_seconds),
		"unique": bool(unique),
		"temporary": False,
		# target_type/target_user can be omitted for a normal invite
	}
	async with httpx.AsyncClient(timeout=10.0) as client:
		response = await client.post(url, headers=_headers(token), json=payload)
		response.raise_for_status()
		return response.json()


async def send_message_to_channel(channel_id: str, token: str, content: str | None = None, embed: dict | None = None) -> dict:
	"""チャンネルにメッセージを送信する

	Args:
		channel_id: チャンネル ID
		token: Bot トークン
		content: メッセージ本文（テキスト）
		embed: 埋め込みオブジェクト（Discord Embed形式）

	Returns:
		送信されたメッセージのペイロード
	"""
	url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
	payload: dict = {}
	
	if content:
		payload["content"] = content
	if embed:
		payload["embeds"] = [embed] if isinstance(embed, dict) else embed
	
	if not payload:
		raise ValueError("content or embed must be provided")
	
	async with httpx.AsyncClient(timeout=10.0) as client:
		response = await client.post(url, headers=_headers(token), json=payload)
		response.raise_for_status()
		return response.json()
