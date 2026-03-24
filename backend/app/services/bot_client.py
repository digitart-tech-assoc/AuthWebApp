"""役割: Bot通知クライアント"""

from __future__ import annotations

import os

import httpx


BOT_INTERNAL_URL = os.getenv("BOT_INTERNAL_URL", "http://discord-bot:8000/internal/sync")
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")


async def notify_bot_sync() -> dict:
	"""Botへ同期要求を送る最小クライアント。"""
	headers = {"Authorization": f"Bearer {SHARED_SECRET}"}
	payload = {"action": "sync_roles"}
	async with httpx.AsyncClient(timeout=5.0) as client:
		response = await client.post(BOT_INTERNAL_URL, json=payload, headers=headers)
	return {"status_code": response.status_code, "body": response.text}
