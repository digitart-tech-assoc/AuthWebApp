"""役割: 認証ヘッダー検証（Supabase JWT + DB正本RBAC）"""

from __future__ import annotations

import os
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException

from app.db.user_repository import get_user_role, upsert_user


SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


def _extract_bearer_token(authorization: str | None) -> str:
	if not authorization:
		raise HTTPException(status_code=401, detail="Authorization header is required")
	parts = authorization.split(" ", 1)
	if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
		raise HTTPException(status_code=401, detail="Invalid authorization header")
	return parts[1].strip()


def _decode_supabase_token(token: str) -> dict[str, Any]:
	if not SUPABASE_JWT_SECRET:
		raise HTTPException(status_code=401, detail="SUPABASE_JWT_SECRET is not configured")
	try:
		claims = jwt.decode(
			token,
			SUPABASE_JWT_SECRET,
			algorithms=["HS256"],
			audience="authenticated",
		)
		return claims
	except jwt.PyJWTError as exc:
		raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


def get_current_principal(authorization: str | None = Header(default=None)) -> dict[str, Any]:
	token = _extract_bearer_token(authorization)

	# 内部連携用 shared secret を許容（開発・ボット間通信用）
	if token == SHARED_SECRET:
		return {"auth_type": "internal", "sub": "internal-service", "app_role": "admin"}

	claims = _decode_supabase_token(token)
	sub = claims.get("sub", "")
	if not sub:
		raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")

	# Supabase は user_metadata.provider_id に Discord ID を格納する
	user_metadata = claims.get("user_metadata") or {}
	discord_id_raw: str | None = (
		user_metadata.get("provider_id")
		or user_metadata.get("sub")
		or None
	)

	# DBからroleを取得（DBになければ upsert で 'none' で登録）
	try:
		user = upsert_user(user_id=sub, discord_id=discord_id_raw)
		app_role = user.get("app_role", "none")
		discord_id_effective = user.get("discord_id") or discord_id_raw
	except Exception:
		# DBアクセスに失敗してもJWT検証済みとして処理は通すが、role は none とする
		app_role = "none"
		discord_id_effective = discord_id_raw

	return {
		"auth_type": "user",
		"sub": sub,
		"discord_id": discord_id_effective,
		"app_role": app_role,
		**claims,
	}


def require_member(principal: dict = Depends(get_current_principal)) -> dict:
	"""member / obog / admin のみ許可する FastAPI Dependency。"""
	allowed = {"member", "admin", "obog"}
	if principal.get("app_role") not in allowed:
		raise HTTPException(status_code=403, detail="Membership required")
	return principal


def require_admin(principal: dict = Depends(get_current_principal)) -> dict:
	"""admin のみ許可する FastAPI Dependency。"""
	if principal.get("app_role") != "admin":
		raise HTTPException(status_code=403, detail="Admin access required")
	return principal