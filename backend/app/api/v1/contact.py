"""役割: お問い合わせAPI"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.core.config import CONTACT_RATE_LIMIT, CONTACT_RATE_WINDOW_SECONDS
from app.core.errors import log_exception_without_message
from app.core.rate_limit import SlidingWindowRateLimiter, enforce_rate_limit, get_client_ip
from app.services.discord_client import send_message_to_channel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/contact", tags=["contact"])
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN", "")
CONTACT_CHANNEL_ID = os.getenv("CONTACT_CHANNEL_ID", "1333116246006431816")
# 公開エンドポイントからの Discord チャンネルへのスパム投稿を防ぐ（#82）。IP 単位
_contact_limiter = SlidingWindowRateLimiter(CONTACT_RATE_LIMIT, CONTACT_RATE_WINDOW_SECONDS)


class ContactRequest(BaseModel):
	email: str
	name: str
	subject: str | None = None
	affiliation: str | None = None
	message: str | None = None


@router.post("/submit")
async def submit_contact(request: ContactRequest, http_request: Request) -> dict:
	"""お問い合わせフォーム送信
	
	Args:
		request: お問い合わせ内容
		http_request: クライアント IP の取得に使う
	
	Returns:
		送信結果
	"""
	if not DISCORD_BOT_TOKEN:
		raise HTTPException(status_code=500, detail="Discord bot token is not configured")
	
	if not CONTACT_CHANNEL_ID:
		raise HTTPException(status_code=500, detail="Contact channel ID is not configured")

	await enforce_rate_limit(_contact_limiter, f"ip:{get_client_ip(http_request)}", "contact submit")
	
	# Discord embed を作成
	embed = {
		"title": "📬 新しいお問い合わせ",
		"description": request.subject or "（件名なし）",
		"color": 3447003,  # Blue
		"fields": [
			{
				"name": "📧 メールアドレス",
				"value": request.email,
				"inline": False,
			},
			{
				"name": "👤 氏名",
				"value": request.name or "（未入力）",
				"inline": True,
			},
			{
				"name": "🏫 所属",
				"value": request.affiliation or "（未入力）",
				"inline": True,
			},
			{
				"name": "💬 本文",
				"value": request.message or "（未入力）",
				"inline": False,
			},
		],
		"footer": {
			"text": f"受信時刻: {datetime.now(timezone.utc).isoformat()}"
		},
	}
	
	try:
		result = await send_message_to_channel(
			channel_id=CONTACT_CHANNEL_ID,
			token=DISCORD_BOT_TOKEN,
			embed=embed,
		)
		return {
			"status": "success",
			"message": "お問い合わせを送信しました",
			"message_id": result.get("id"),
		}
	except Exception as e:
		# 例外メッセージには Discord の応答本文（問い合わせ内容を含みうる）が入るため出さない
		log_exception_without_message(logger, "send contact message to Discord", e)
		raise HTTPException(status_code=500, detail="Failed to send message")
