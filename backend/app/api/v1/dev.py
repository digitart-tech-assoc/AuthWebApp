"""役割: 開発環境専用 — ロール切替API

本番環境（FASTAPI_ENV=production など DEV_ENVS に含まれない環境）では自動的に無効化される。
ブラウザ上のDevRoleSwitcherモーダルから呼び出される。
内部サービス間通信（SHARED_SECRET 経由）の principal でも開発環境であればアクセス可能
（テストや自動化対応を許容。ただし switch_role 実行時は対象の Discord ID の解決が必要）。
"""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_principal
from app.core.constants import DEV_ENVS
from app.db.connection import _connect

logger = logging.getLogger(__name__)


def _verify_dev_env() -> None:
	"""本番環境や未設定環境では 404 を返し、APIを完全に遮断する（多層防御・ホワイトリスト方式）。"""
	env = os.getenv("FASTAPI_ENV", "").strip().lower()
	if env not in DEV_ENVS:
		raise HTTPException(status_code=404, detail="Not Found")


router = APIRouter(
	prefix="/api/v1/dev",
	tags=["dev"],
	dependencies=[Depends(_verify_dev_env)],
)

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


def _switch_role_tx(discord_id: str, target_role: str, is_paid: bool) -> None:
	"""指定 discord_id のロールと支払い状態を単一トランザクションでアトミックに切り替える。"""
	conn = _connect()
	try:
		with conn.cursor() as cur:
			# 1. 既存の全メンバーシップおよび支払い招待レコードを削除
			cur.execute(
				"DELETE FROM user_memberships WHERE discord_id = %s",
				(discord_id,),
			)
			cur.execute(
				"DELETE FROM paid_invitations WHERE discord_id = %s",
				(discord_id,),
			)

			# 2. 新ロールを追加（'none' の場合はメンバーシップなし）
			if target_role != "none":
				cur.execute(
					"""
					INSERT INTO user_memberships (discord_id, membership_type, assigned_by, assigned_at, created_at)
					VALUES (%s, %s, 'dev-switcher', now(), now())
					ON CONFLICT (discord_id, membership_type) DO NOTHING
					""",
					(discord_id, target_role),
				)

			# 3. 支払いフラグが有効な場合は paid_invitations を登録
			if is_paid:
				cur.execute(
					"""
					INSERT INTO paid_invitations (discord_id, note, assigned_by)
					VALUES (%s, 'dev-switcher', 'dev-switcher')
					ON CONFLICT (discord_id) DO UPDATE SET note = 'dev-switcher', assigned_by = 'dev-switcher', assigned_at = now()
					""",
					(discord_id,),
				)

		conn.commit()
	except Exception:
		conn.rollback()
		raise
	finally:
		conn.close()


def _get_current_state(discord_id: str) -> tuple[str, bool]:
	"""現在のロールと支払い状態を単一接続・単一トランザクションで取得する。

	優先度順位: admin > member > sub_user > pre_member > obog (memberをsub_userより明確に優先)
	"""
	conn = _connect()
	try:
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
				END, membership_type ASC
				LIMIT 1
				""",
				(discord_id,),
			)
			row = cur.fetchone()
			current_role = row[0] if row else "none"

			cur.execute(
				"""
				SELECT 1 FROM paid_invitations
				WHERE discord_id = %s
				  AND (expires_at IS NULL OR expires_at > now())
				""",
				(discord_id,),
			)
			is_paid = cur.fetchone() is not None

		return current_role, is_paid
	finally:
		conn.close()


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

	current_role, is_paid = await asyncio.to_thread(_get_current_state, discord_id)

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

	# 単一トランザクションでアトミックにロールと支払いフラグを切り替え
	await asyncio.to_thread(_switch_role_tx, discord_id, target_role, body.is_paid)

	# 結果を単一接続で取得
	final_role, final_paid = await asyncio.to_thread(_get_current_state, discord_id)

	return SwitchRoleResponse(
		success=True,
		discord_id=discord_id,
		new_role=final_role,
		is_paid=final_paid,
		message=f"ロールを {final_role} に切り替えました{'（入会費支払済）' if final_paid else ''}",
	)
