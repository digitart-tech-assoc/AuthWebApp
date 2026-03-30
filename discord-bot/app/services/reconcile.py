"""役割: 差分同期ロジック

このモジュールでは Discord Bot がバックエンドの `member_list` / `pre_member_list` を取得し、
Discord 側のロール付与/剥奪を行います。
"""

from __future__ import annotations

import os
import typing

import httpx


BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")
PRE_MEMBER_ROLE_ID = os.getenv("PRE_MEMBER_ROLE_ID", "")
MEMBER_ROLE_IDS = os.getenv("MEMBER_ROLE_IDS", "")  # comma separated


async def _add_role(client: httpx.AsyncClient, user_id: str, role_id: str) -> tuple[bool, int, str | None]:
	url = f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{user_id}/roles/{role_id}"
	try:
		resp = await client.put(url, headers={"Authorization": f"Bot {DISCORD_TOKEN}"})
		return (resp.status_code in (200, 201, 204), resp.status_code, resp.text)
	except Exception as e:
		return (False, 0, str(e))


async def _remove_role(client: httpx.AsyncClient, user_id: str, role_id: str) -> tuple[bool, int, str | None]:
	url = f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{user_id}/roles/{role_id}"
	try:
		resp = await client.delete(url, headers={"Authorization": f"Bot {DISCORD_TOKEN}"})
		return (resp.status_code in (200, 201, 204), resp.status_code, resp.text)
	except Exception as e:
		return (False, 0, str(e))


async def run_reconcile() -> dict:
	"""Fetch member/pre_member lists from backend and reconcile roles in Discord.

	Returns a summary dict with counts and any errors encountered.
	"""
	if not BACKEND_URL or not SHARED_SECRET:
		return {"ok": False, "error": "BACKEND_URL or SHARED_SECRET not configured"}
	if not DISCORD_TOKEN or not DISCORD_GUILD_ID:
		return {"ok": False, "error": "DISCORD_TOKEN or DISCORD_GUILD_ID not configured"}

	member_role_ids = [r.strip() for r in MEMBER_ROLE_IDS.split(",") if r.strip()]

	async with httpx.AsyncClient(timeout=20.0) as client:
		# 1) Get lists from backend internal endpoint
		try:
			resp = await client.get(
				f"{BACKEND_URL}/api/v1/members/internal/lists",
				headers={"Authorization": f"Bearer {SHARED_SECRET}"},
				timeout=10.0,
			)
		except Exception as e:
			return {"ok": False, "error": f"failed to fetch lists: {e}"}

		if resp.status_code != 200:
			return {"ok": False, "error": f"lists fetch failed: {resp.status_code}", "body": resp.text}

		payload = resp.json()
		data = payload.get("data") if isinstance(payload, dict) and payload.get("data") is not None else payload
		lists = data or {}

		member_list = [str(x.get("discord_id")) for x in lists.get("member_list", [])]
		pre_member_list = [str(x.get("discord_id")) for x in lists.get("pre_member_list", [])]

		added = 0
		removed = 0
		errors: list[str] = []

		# 2) Ensure members have member roles and do not have pre-member role
		for uid in member_list:
			# add member roles
			for rid in member_role_ids:
				ok, status, body = await _add_role(client, uid, rid)
				if ok:
					added += 1
				else:
					# ignore 404 (user not in guild) but record other errors
					if status not in (404,):
						errors.append(f"add {rid} to {uid} failed: {status} {body}")

			# remove pre-member role if configured
			if PRE_MEMBER_ROLE_ID:
				ok, status, body = await _remove_role(client, uid, PRE_MEMBER_ROLE_ID)
				if ok:
					removed += 1
				else:
					if status not in (404,):
						errors.append(f"remove pre-role {PRE_MEMBER_ROLE_ID} from {uid} failed: {status} {body}")

		# 3) Ensure pre-members have pre_member role (if not members)
		for uid in pre_member_list:
			if uid in member_list:
				continue
			if PRE_MEMBER_ROLE_ID:
				ok, status, body = await _add_role(client, uid, PRE_MEMBER_ROLE_ID)
				if ok:
					added += 1
				else:
					if status not in (404,):
						errors.append(f"add pre-role {PRE_MEMBER_ROLE_ID} to {uid} failed: {status} {body}")

	return {"ok": len(errors) == 0, "added": added, "removed": removed, "errors": errors}
