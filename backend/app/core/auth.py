"""役割: 認証ヘッダー検証（Keycloak JWT + DB正本RBAC）"""

from __future__ import annotations

import asyncio
import os
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException

from app.db.user_repository import find_discord_id_by_keycloak_sub, get_user_role, upsert_user


SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")
KEYCLOAK_ISSUER_URL = os.getenv("KEYCLOAK_ISSUER_URL", "").strip()
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "").strip()
KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL", "").strip()


def _parse_audience_config() -> str | list[str] | None:
	if not KEYCLOAK_AUDIENCE:
		return None

	normalized = KEYCLOAK_AUDIENCE.strip().lower()
	if normalized in {"off", "none", "false", "*"}:
		return None

	parts = [part.strip() for part in KEYCLOAK_AUDIENCE.split(",") if part.strip()]
	if not parts:
		return None
	if len(parts) == 1:
		return parts[0]
	return parts


def _extract_bearer_token(authorization: str | None) -> str:
	if not authorization:
		raise HTTPException(status_code=401, detail="Authorization header is required")
	parts = authorization.split(" ", 1)
	if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
		raise HTTPException(status_code=401, detail="Invalid authorization header")
	return parts[1].strip()


@lru_cache(maxsize=1)
def _get_jwk_client() -> jwt.PyJWKClient | None:
	if KEYCLOAK_JWKS_URL:
		return jwt.PyJWKClient(KEYCLOAK_JWKS_URL)
	if not KEYCLOAK_ISSUER_URL:
		return None
	return jwt.PyJWKClient(f"{KEYCLOAK_ISSUER_URL.rstrip('/')}/protocol/openid-connect/certs")


def _decode_keycloak_token(token: str) -> dict[str, Any]:
	if not KEYCLOAK_ISSUER_URL:
		raise HTTPException(status_code=401, detail="Keycloak is not configured")

	jwk_client = _get_jwk_client()
	if jwk_client is None:
		raise HTTPException(status_code=401, detail="Keycloak JWKS is not configured")

	try:
		signing_key = jwk_client.get_signing_key_from_jwt(token)
		audience = _parse_audience_config()
		decode_options: dict[str, Any] = {
			"algorithms": ["RS256"],
			"issuer": KEYCLOAK_ISSUER_URL,
		}
		if audience is not None:
			decode_options["audience"] = audience
		else:
			decode_options["options"] = {"verify_aud": False}
		claims = jwt.decode(token, signing_key.key, **decode_options)
		return claims
	except jwt.PyJWTError as exc:
		raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


def get_current_principal(authorization: str | None = Header(default=None)) -> dict[str, Any]:
	token = _extract_bearer_token(authorization)

	# 内部連携用 shared secret を許容（開発・ボット間通信用）
	if token == SHARED_SECRET:
		return {"auth_type": "internal", "sub": "internal-service", "app_role": "admin"}

	claims = _decode_keycloak_token(token)
	sub = claims.get("sub", "")
	if not sub:
		raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")

	# Discord IdP 経由のsubから discord_id を抽出
	# Keycloak が discord IdP を使う場合、sub は "discord:12345..." または単純な数値ID になる
	discord_id_raw: str | None = None
	if "discord:" in sub:
		discord_id_raw = sub.split("discord:", 1)[-1]
	elif sub.isdigit():
		discord_id_raw = sub

	# sub が UUID 形式の場合は Keycloak federated_identity から discord_id を解決
	if not discord_id_raw:
		try:
			discord_id_raw = find_discord_id_by_keycloak_sub(sub)
		except Exception:
			discord_id_raw = None

	# DBからroleを取得（DBになければ upsert で 'none' で登録）
	try:
		user = upsert_user(keycloak_sub=sub, discord_id=discord_id_raw)
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