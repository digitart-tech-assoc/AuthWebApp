"""役割: ユーザー認証・登録 API"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_principal
from app.db.user_repository import find_user_by_sub, is_paid_invitation


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class UserMeResponse(BaseModel):
	sub: str
	discord_id: str | None
	app_role: str
	is_paid: bool = False


@router.post("/login-or-register", response_model=UserMeResponse)
async def login_or_register(principal: dict = Depends(get_current_principal)) -> UserMeResponse:
	"""ログイン後に呼び出し、ユーザーをDBに登録しロールを返す。
	auth.py の get_current_principal がすでに upsert を行うため、ここでは取得のみ行う。
	"""
	sub = principal.get("sub", "")
	discord_id = principal.get("discord_id", sub)
	app_role = principal.get("app_role", "none")

	# paid_invitations を確認
	paid = False
	if discord_id and app_role == "none":
		paid = await asyncio.to_thread(is_paid_invitation, discord_id)

	return UserMeResponse(
		sub=sub,
		discord_id=discord_id,
		app_role=app_role,
		is_paid=paid,
	)


@router.get("/me", response_model=UserMeResponse)
async def get_me(principal: dict = Depends(get_current_principal)) -> UserMeResponse:
	"""現在のユーザー情報を返す。"""
	sub = principal.get("sub", "")
	discord_id = principal.get("discord_id", sub)
	app_role = principal.get("app_role", "none")

	paid = False
	if discord_id and app_role == "none":
		paid = await asyncio.to_thread(is_paid_invitation, discord_id)

	return UserMeResponse(
		sub=sub,
		discord_id=discord_id,
		app_role=app_role,
		is_paid=paid,
	)
