"""役割: 開発環境専用 — ロール切替API

本番環境（FASTAPI_ENV=production）では自動的に無効化される。
ブラウザ上のDevRoleSwitcherモーダルから呼び出される。
"""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_principal
from app.db.connection import _connect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dev", tags=["dev"])

# 許可するロール値
ALLOWED_ROLES = {"admin", "member", "pre_member", "obog", "sub_user", "none"}


class SwitchRoleRequest(BaseModel):
	"""ロール切替リクエスト"""
	role: str
	is_paid: bool = False


class SwitchRoleResponse(BaseModel):
	"""ロール切替レスポンス"""
	success: bool
	discord_id: str | None
	new_role: str
	is_paid: bool
	message: str


class CurrentDevState(BaseModel):
	"""現在のdev状態"""
	discord_id: str | None
	current_role: str
	is_paid: bool
	available_roles: list[str]


def _clear_memberships(discord_id: str) -> None:
	"""指定 discord_id の全メンバーシップを削除する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"DELETE FROM user_memberships WHERE discord_id = %s",
				(discord_id,)
			)
			conn.commit()


def _clear_paid_invitation(discord_id: str) -> None:
	"""指定 discord_id の paid_invitations を削除する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"DELETE FROM paid_invitations WHERE discord_id = %s",
				(discord_id,)
			)
			conn.commit()


def _add_membership(discord_id: str, membership_type: str) -> None:
	"""メンバーシップを追加する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
				VALUES (%s, %s, 'dev-switcher', now(), now())
				ON CONFLICT (discord_id, membership_type) DO NOTHING
				""",
				(discord_id, membership_type)
			)
			conn.commit()


def _add_paid_invitation(discord_id: str) -> None:
	"""paid_invitations にレコードを追加する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				INSERT INTO paid_invitations (discord_id, note, assigned_by)
				VALUES (%s, 'dev-switcher', 'dev-switcher')
				ON CONFLICT (discord_id) DO UPDATE SET note = 'dev-switcher', assigned_by = 'dev-switcher', assigned_at = now()
				""",
				(discord_id,)
			)
			conn.commit()


def _get_current_role(discord_id: str) -> str:
	"""user_memberships から現在のロールを取得する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT membership_type FROM user_memberships
				WHERE discord_id = %s
				ORDER BY CASE membership_type
					WHEN 'admin' THEN 1
					WHEN 'member' THEN 2
					WHEN 'sub_user' THEN 3
					WHEN 'pre_member' THEN 4
					WHEN 'obog' THEN 5
					ELSE 6
				END LIMIT 1
				""",
				(discord_id,)
			)
			row = cur.fetchone()
			if row is None:
				return "none"
			return row[0]


def _is_paid(discord_id: str) -> bool:
	"""paid_invitations に存在するか確認する。"""
	with _connect() as conn:
		with conn.cursor() as cur:
			cur.execute(
				"""
				SELECT 1 FROM paid_invitations
				WHERE discord_id = %s
				  AND (expires_at IS NULL OR expires_at > now())
				""",
				(discord_id,)
			)
			return cur.fetchone() is not None


@router.get("/state", response_model=CurrentDevState)
async def get_dev_state(
	principal: dict = Depends(get_current_principal),
) -> CurrentDevState:
	"""現在のユーザーのdev状態を取得する。"""
	discord_id = principal.get("discord_id")
	if not discord_id:
		return CurrentDevState(
			discord_id=None,
			current_role="none",
			is_paid=False,
			available_roles=sorted(ALLOWED_ROLES),
		)

	current_role = await asyncio.to_thread(_get_current_role, discord_id)
	is_paid = await asyncio.to_thread(_is_paid, discord_id)

	return CurrentDevState(
		discord_id=discord_id,
		current_role=current_role,
		is_paid=is_paid,
		available_roles=sorted(ALLOWED_ROLES),
	)


@router.post("/switch-role", response_model=SwitchRoleResponse)
async def switch_role(
	body: SwitchRoleRequest,
	principal: dict = Depends(get_current_principal),
) -> SwitchRoleResponse:
	"""ロールを切り替える（user_memberships + paid_invitations を操作）。"""
	discord_id = principal.get("discord_id")
	if not discord_id:
		raise HTTPException(
			status_code=400,
			detail="Discord IDが紐づいていないため、ロール切替できません。Discord OAuthでログインしてください。"
		)

	target_role = body.role
	if target_role not in ALLOWED_ROLES:
		raise HTTPException(
			status_code=400,
			detail=f"無効なロール: {target_role}。許可: {sorted(ALLOWED_ROLES)}"
		)

	logger.info(
		"[Dev] Role switch: discord_id=%s, target_role=%s, is_paid=%s",
		discord_id, target_role, body.is_paid,
	)

	# 1. 全メンバーシップをクリア
	await asyncio.to_thread(_clear_memberships, discord_id)
	# 2. paid_invitations をクリア
	await asyncio.to_thread(_clear_paid_invitation, discord_id)

	# 3. 新しいメンバーシップを追加（none 以外）
	if target_role != "none":
		await asyncio.to_thread(_add_membership, discord_id, target_role)

	# 4. is_paid フラグに基づいて paid_invitations を操作
	if body.is_paid:
		await asyncio.to_thread(_add_paid_invitation, discord_id)

	# 結果を確認
	final_role = await asyncio.to_thread(_get_current_role, discord_id)
	final_paid = await asyncio.to_thread(_is_paid, discord_id)

	return SwitchRoleResponse(
		success=True,
		discord_id=discord_id,
		new_role=final_role,
		is_paid=final_paid,
		message=f"ロールを {final_role} に切り替えました{'（入会費支払済）' if final_paid else ''}",
	)
