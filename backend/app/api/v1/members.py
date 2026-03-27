"""役割: メンバー管理 API"""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.db.repository import register_pre_member


router = APIRouter(prefix="/api/v1/members", tags=["members"])
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")


class PreMemberRequest(BaseModel):
	discord_id: str


@router.post("/pre_member/register")
async def register_pre_member_endpoint(
	payload: PreMemberRequest,
	authorization: str | None = Header(default=None),
) -> dict:
	"""Discord bot から新しい参加者を pre_member_list に登録する内部エンドポイント。
	
	認証: SHARED_SECRET によるベアラートークン認証
	"""
	expected = f"Bearer {SHARED_SECRET}"
	if authorization != expected:
		raise HTTPException(status_code=401, detail="Unauthorized")
	
	try:
		result = await asyncio.to_thread(register_pre_member, payload.discord_id)
		return {"ok": True, "discord_id": payload.discord_id, "result": result}
	except Exception as e:
		raise HTTPException(status_code=400, detail=str(e))
