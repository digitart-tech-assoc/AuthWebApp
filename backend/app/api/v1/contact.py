"""役割: お問い合わせAPI"""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.services.discord_client import send_message_to_channel


router = APIRouter(prefix="/api/v1/contact", tags=["contact"])
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN", "")
CONTACT_CHANNEL_ID = os.getenv("CONTACT_CHANNEL_ID", "1333116246006431816")


class ContactRequest(BaseModel):
	email: str
	name: str
	subject: str | None = None
	affiliation: str | None = None
	message: str | None = None


@router.post("/submit")
async def submit_contact(request: ContactRequest) -> dict:
	"""お問い合わせフォーム送信
	
	Args:
		request: お問い合わせ内容
	
	Returns:
		送信結果
	"""
	if not DISCORD_BOT_TOKEN:
		raise HTTPException(status_code=500, detail="Discord bot token is not configured")
	
	if not CONTACT_CHANNEL_ID:
		raise HTTPException(status_code=500, detail="Contact channel ID is not configured")
	
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
			"text": f"受信時刻: {datetime.utcnow().isoformat()}Z"
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
		print(f"[ERROR] Failed to send contact message to Discord: {e}")
		import traceback
		traceback.print_exc()
		raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")
