"""役割: メンバー管理 API"""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel

from app.core.auth import require_admin
from app.db.repository import (
	register_pre_member,
	get_pre_member_list_with_users,
	add_to_member_list,
	register_paid_invitation,
)
from app.services.discord_client import fetch_guild_member


router = APIRouter(prefix="/api/v1/members", tags=["members"])
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")


class PreMemberRequest(BaseModel):
	discord_id: str


class AddMemberRequest(BaseModel):
	discord_id: str
	note: str | None = None


class PaidInvitationRequest(BaseModel):
	discord_id: str
	note: str | None = None


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


@router.get("/pre_member/list")
async def get_pre_member_list(
	search: str | None = Query(None),
	_principal: dict = Depends(require_admin),
) -> dict:
	"""Pre-member一覧を取得（admin のみ）。
	
	クエリパラメータ:
	- search: user_id または discord_id で検索
	
	Discord APIからユーザー名を取得して附属させる。
	"""
	try:
		result = await asyncio.to_thread(get_pre_member_list_with_users, search)
		
		# Discord API から各ユーザーの username を取得
		if DISCORD_TOKEN and DISCORD_GUILD_ID:
			for member in result:
				try:
					discord_member = await fetch_guild_member(
						DISCORD_GUILD_ID,
						member["discord_id"],
						DISCORD_TOKEN
					)
					if discord_member:
						member["discord_username"] = discord_member["username"]
						member["discord_display_name"] = discord_member["display_name"]
					else:
						member["discord_username"] = "(not found)"
						member["discord_display_name"] = None
				except Exception as e:
					print(f"Failed to fetch Discord user {member['discord_id']}: {e}")
					member["discord_username"] = "(error)"
					member["discord_display_name"] = None
		else:
			for member in result:
				member["discord_username"] = "(token not configured)"
				member["discord_display_name"] = None
		
		return {"ok": True, "data": result}
	except Exception as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.post("/member/add")
async def add_member(
	payload: AddMemberRequest,
	_principal: dict = Depends(require_admin),
) -> dict:
	"""Pre-member を member_list に追加（admin のみ）。
	
	同時に paid_invitations にも登録する場合必要があれば。
	"""
	try:
		assigned_by = _principal.get("discord_id") or _principal.get("sub", "unknown")
		result = await asyncio.to_thread(
			add_to_member_list,
			payload.discord_id,
			assigned_by,
			payload.note,
		)
		return {"ok": True, "data": result}
	except ValueError as e:
		raise HTTPException(status_code=400, detail=str(e))
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/paid_invitation/register")
async def register_paid_invitation_endpoint(
	payload: PaidInvitationRequest,
	_principal: dict = Depends(require_admin),
) -> dict:
	"""入会費支払い済みユーザーを paid_invitations に登録（admin のみ）。"""
	try:
		result = await asyncio.to_thread(
			register_paid_invitation,
			payload.discord_id,
			payload.note,
		)
		return {"ok": True, "data": result}
	except Exception as e:
		raise HTTPException(status_code=400, detail=str(e))
