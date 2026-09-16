"""役割: 認証ヘッダー検証（Supabase JWT + DB正本RBAC）"""

from __future__ import annotations

import os
import logging
logger = logging.getLogger(__name__)
from typing import Any

import jwt
from jwt import PyJWKClient
from fastapi import Depends, Header, HTTPException

from app.db.user_repository import get_user_role, upsert_user


SHARED_SECRET = os.getenv("SHARED_SECRET", "")

# Supabase JWT 署名検証用シークレット（従来のHS256用）
SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

# Supabase の URL（JWKSのエンドポイント組み立て等に使用）
SUPABASE_URL: str = (os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL") or "").rstrip("/")
JWKS_URL: str = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else ""
jwks_client = PyJWKClient(JWKS_URL) if JWKS_URL else None


def _get_jwks_client() -> PyJWKClient | None:
	"""JWKSクライアントを取得する。環境変数 SUPABASE_URL が設定されている場合のみ初期化。"""
	global jwks_client
	if jwks_client is not None:
		return jwks_client

	if SUPABASE_URL:
		jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
		logger.info("Initializing PyJWKClient with JWKS URL: %s", jwks_url)
		jwks_client = PyJWKClient(jwks_url)
		return jwks_client

	return None

# Supabase の issuer URL（任意: 設定時に iss クレームも検証する）
SUPABASE_ISSUER_URL: str = os.getenv("SUPABASE_ISSUER_URL", "")


def _extract_bearer_token(authorization: str | None) -> str:
	if not authorization:
		raise HTTPException(status_code=401, detail="Authorization header is required")
	parts = authorization.split()
	if len(parts) != 2 or parts[0].lower() != "bearer":
		raise HTTPException(status_code=401, detail="Invalid Authorization header format")
	return parts[1]


def _decode_supabase_token(token: str) -> dict[str, Any]:
	"""Supabase からの JWT を署名検証付きでデコードする。

	ES256/RS256 などの非対称署名の場合は JWKS エンドポイントから公開鍵を動的に取得する。
	HS256 署名の場合は環境変数の SUPABASE_JWT_SECRET で検証する。
	"""
	decode_options: dict[str, Any] = {
		"verify_signature": True,
		"verify_exp": True,
		"verify_aud": True,
	}

	if SUPABASE_ISSUER_URL:
		decode_options["verify_iss"] = True
	else:
		decode_options["verify_iss"] = False

	try:
		# トークンヘッダーからアルゴリズムを判定
		unverified_header = jwt.get_unverified_header(token)
		alg = unverified_header.get("alg")

		if alg in ["RS256", "ES256"]:
			client = _get_jwks_client()
			if not client:
				logger.error("SUPABASE_URL is not configured to verify %s token via JWKS", alg)
				raise HTTPException(
					status_code=500,
					detail=f"Server misconfiguration: SUPABASE_URL is required for {alg} token verification",
				)
			signing_key = client.get_signing_key_from_jwt(token)
			key = signing_key.key
			algorithms = ["RS256", "ES256"]
		else:
			# 従来の対称キー (HS256) の場合
			key = SUPABASE_JWT_SECRET
			algorithms = ["HS256"]
			if not key:
				logger.error("SUPABASE_JWT_SECRET is not set for HS256 (alg=%s)", alg)
				raise HTTPException(
					status_code=500,
					detail=f"Server misconfiguration: SUPABASE_JWT_SECRET is missing for HS256 (alg={alg})",
				)

		kwargs: dict[str, Any] = {
			"jwt": token,
			"key": key,
			"algorithms": algorithms,
			"audience": "authenticated",
			"options": decode_options,
		}
		if SUPABASE_ISSUER_URL:
			kwargs["issuer"] = SUPABASE_ISSUER_URL

		claims = jwt.decode(**kwargs)
		if not claims.get("sub"):
			raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
		return claims
	except jwt.ExpiredSignatureError:
		logger.warning("JWT Expired")
		raise HTTPException(status_code=401, detail="Token has expired")
	except jwt.InvalidAudienceError:
		logger.error(f"JWT Invalid Audience | token: {token}")
		raise HTTPException(status_code=401, detail="Invalid token: audience mismatch")
	except jwt.InvalidIssuerError:
		logger.error(f"JWT Invalid Issuer | token: {token}")
		raise HTTPException(status_code=401, detail="Invalid token: issuer mismatch")
	except jwt.InvalidAlgorithmError:
		logger.error(f"JWT Invalid Algorithm | token: {token}")
		raise HTTPException(status_code=401, detail="Invalid token: algorithm not allowed")
	except jwt.PyJWTError as exc:
		logger.error(f"JWT Decode Failed: {exc}")
		raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


def _extract_verified_discord_id(claims: dict[str, Any]) -> str | None:
	"""Supabase JWTから改ざん不可能な検証済みDiscord IDを抽出する。

	エンドユーザーによる user_metadata 改ざん攻撃を防ぐため、
	OAuth プロバイダ（Discord）経由の認証であること（app_metadata.provider == 'discord'）
	または署名済み identities を検証する。
	"""
	app_metadata = claims.get("app_metadata") or {}
	user_metadata = claims.get("user_metadata") or {}

	# 1. identities クレームが存在する場合は最優先（provider == "discord" の ID）
	identities = claims.get("identities")
	if isinstance(identities, list):
		for identity in identities:
			if identity.get("provider") == "discord":
				discord_id = (
					identity.get("id")
					or identity.get("identity_data", {}).get("sub")
					or identity.get("identity_data", {}).get("provider_id")
				)
				if discord_id:
					return str(discord_id)

	# 2. app_metadata 内に discord_id が安全に付与されている場合
	if isinstance(app_metadata, dict) and app_metadata.get("discord_id"):
		return str(app_metadata["discord_id"])

	# 3. OAuth プロバイダが Discord であることを検証した上でのみ user_metadata をフォールバック利用
	# （Email/Password 等の別プロバイダからの user_metadata.provider_id 偽装を遮断）
	provider = app_metadata.get("provider")
	providers = app_metadata.get("providers") or []
	is_discord_provider = provider == "discord" or "discord" in providers

	if is_discord_provider:
		discord_id_candidate = user_metadata.get("provider_id") or user_metadata.get("sub")
		if discord_id_candidate:
			return str(discord_id_candidate)

	logger.warning(
		"No verified Discord identity found for user %s (app_metadata=%s)",
		claims.get("sub"),
		app_metadata,
	)
	return None


def get_current_principal(authorization: str | None = Header(default=None)) -> dict[str, Any]:
	try:
		token = _extract_bearer_token(authorization)
	except HTTPException as e:
		logger.error(f"Extract Token Failed: {e.detail}")
		raise e

	# 内部連携用 shared secret を許容（開発・ボット間通信用）
	if SHARED_SECRET and token == SHARED_SECRET:
		return {"auth_type": "internal", "sub": "internal-service", "app_role": "admin"}

	try:
		claims = _decode_supabase_token(token)
	except HTTPException as e:
		logger.error(f"Decode Token Failed: {e.detail}")
		raise e
	except Exception as e:
		logger.error(f"Decode Token Unknown Error: {e}")
		raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

	sub = claims.get("sub", "")
	if not sub:
		logger.error("Missing sub claim")
		raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")

	# 改ざん不可能な安全な方法で Discord ID を解決する
	discord_id_raw = _extract_verified_discord_id(claims)

	# DBからroleを取得（DBになければ upsert で 'none' で登録）
	try:
		user = upsert_user(user_id=sub, discord_id=discord_id_raw)
		db_app_role = user.get("app_role", "none")
		discord_id_effective = user.get("discord_id") or discord_id_raw
	except Exception:
		# DBアクセスに失敗してもJWT検証済みとして処理は通すが、role は none とする
		db_app_role = "none"
		discord_id_effective = discord_id_raw

	# JWTクレーム（ルートまたは app_metadata内）に app_role があればそれを優先する
	jwt_app_role = claims.get("app_role")
	if not jwt_app_role and isinstance(claims.get("app_metadata"), dict):
		jwt_app_role = claims["app_metadata"].get("app_role")

	final_app_role = jwt_app_role if jwt_app_role else db_app_role

	return {
		**claims,
		"auth_type": "user",
		"sub": sub,
		"discord_id": discord_id_effective,
		"app_role": final_app_role,
	}


def require_member(principal: dict = Depends(get_current_principal)) -> dict:
	"""member / sub_user / obog / admin のみ許可する FastAPI Dependency。"""
	allowed = {"member", "sub_user", "admin", "obog"}
	if principal.get("app_role") not in allowed:
		raise HTTPException(status_code=403, detail="Membership required")
	return principal


def require_admin(principal: dict = Depends(get_current_principal)) -> dict:
	"""admin のみ許可する FastAPI Dependency。"""
	if principal.get("app_role") != "admin":
		raise HTTPException(status_code=403, detail="Admin access required")
	return principal