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
    cleanup_expired_prospective_members,
    get_member_lists,
)
from app.services.discord_client import fetch_guild_member


router = APIRouter(prefix="/api/v1/members", tags=["members"])
SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID", "")


class PreMemberRequest(BaseModel):
	discord_id: str
	source: str | None = None  # 'P' = prospective, 'S' = student


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
		result = await asyncio.to_thread(register_pre_member, payload.discord_id, payload.source)
		return {"ok": True, "discord_id": payload.discord_id, "result": result}
	except Exception as e:
		raise HTTPException(status_code=400, detail=str(e))


@router.get("/internal/lists")
async def internal_get_lists(authorization: str | None = Header(default=None)) -> dict:
	"""内部用: member_list/admin_list/pre_member_list を取得（Discord ボット専用）。

	認証: SHARED_SECRET によるベアラートークン
	"""
	expected = f"Bearer {SHARED_SECRET}"
	if authorization != expected:
		raise HTTPException(status_code=401, detail="Unauthorized")

	try:
		result = await asyncio.to_thread(get_member_lists)
		return {"ok": True, "data": result}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/pre_member/cleanup")
async def cleanup_pre_members_endpoint(
	authorization: str | None = Header(default=None),
) -> dict:
	"""Trigger cleanup of expired prospective pre-members.

	Intended to be called by the discord-bot (internal), protected by SHARED_SECRET.
	"""
	expected = f"Bearer {SHARED_SECRET}"
	if authorization != expected:
		raise HTTPException(status_code=401, detail="Unauthorized")

	try:
		result = await asyncio.to_thread(cleanup_expired_prospective_members)
		return {"ok": True, "data": result}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/pre_member/list")
async def get_pre_member_list(
	search: str | None = Query(None),
	_principal: dict = Depends(require_admin),
) -> dict:
	"""Pre-member一覧を取得（admin のみ）。
	
	クエリパラメータ:
	- search: discord_id で検索
	
	Discord APIからユーザー名を取得して附属させる。
	"""
	try:
		result = await asyncio.to_thread(get_pre_member_list_with_users, search)
		
		# Discord API から各ユーザーの username を取得（セマフォで並列化 + リトライ付き）
		if DISCORD_TOKEN and DISCORD_GUILD_ID:
			concurrency = 5
			max_retries = 2
			sem = asyncio.Semaphore(concurrency)

			async def _fetch_with_sem(member):
				async with sem:
					for attempt in range(max_retries + 1):
						try:
							result_member = await fetch_guild_member(
								DISCORD_GUILD_ID,
								member["discord_id"],
								DISCORD_TOKEN,
							)
							if result_member is None:
								if attempt < max_retries:
									await asyncio.sleep(0.5 * (attempt + 1))
									continue
								else:
									return None
							return result_member
						except Exception as e:
							if attempt < max_retries:
								print(f"[RETRY {attempt+1}] Failed to fetch Discord user {member['discord_id']}: {e}")
								await asyncio.sleep(0.5 * (attempt + 1))
							else:
								print(f"[FAILED] Fetch Discord user {member['discord_id']} failed after {max_retries + 1} attempts: {e}")
								return None
					return None

			tasks = [_fetch_with_sem(member) for member in result]
			discord_members = await asyncio.gather(*tasks)
			for member, discord_member in zip(result, discord_members):
				if discord_member and isinstance(discord_member, dict):
					# サーバー表示名を優先、なければグローバルユーザー名を使用
					member["discord_username"] = discord_member.get("display_name") or discord_member.get("username") or "(unknown)"
					member["discord_display_name"] = discord_member.get("display_name")
				else:
					member["discord_username"] = "(ユーザー情報取得失敗)"
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
		# assigned_by を確実に取得（複数の試行方法）
		assigned_by = (
			_principal.get("discord_id") 
			or _principal.get("sub") 
			or _principal.get("user_id")
			or "unknown"
		)
		
		# ログ出力（デバッグ用）
		import logging
		logger = logging.getLogger(__name__)
		logger.info(f"register_paid_invitation: principal={_principal}, assigned_by={assigned_by}")
		
		result = await asyncio.to_thread(
			register_paid_invitation,
			payload.discord_id,
			payload.note,
			assigned_by,
		)
		return {"ok": True, "data": result}
	except Exception as e:
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f"Error in register_paid_invitation: {e}")
		raise HTTPException(status_code=400, detail=str(e))
