"""役割: 認証ヘッダー検証（Keycloak JWT + 一時的内部トークン互換）"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Header, HTTPException


SHARED_SECRET = os.getenv("SHARED_SECRET", "dev-secret")
KEYCLOAK_ISSUER_URL = os.getenv("KEYCLOAK_ISSUER_URL", "").strip()
KEYCLOAK_AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "").strip()
KEYCLOAK_JWKS_URL = os.getenv("KEYCLOAK_JWKS_URL", "").strip()


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
		decode_options: dict[str, Any] = {
			"algorithms": ["RS256"],
			"issuer": KEYCLOAK_ISSUER_URL,
			"options": {"verify_aud": False},
		}
		claims = jwt.decode(token, signing_key.key, **decode_options)

		if KEYCLOAK_AUDIENCE:
			audience_claim = claims.get("aud")
			azp_claim = claims.get("azp")
			aud_match = False

			if isinstance(audience_claim, str):
				aud_match = audience_claim == KEYCLOAK_AUDIENCE
			elif isinstance(audience_claim, list):
				aud_match = KEYCLOAK_AUDIENCE in audience_claim

			if not aud_match and azp_claim != KEYCLOAK_AUDIENCE:
				raise HTTPException(status_code=401, detail="Invalid token audience")

		return claims
	except jwt.PyJWTError as exc:
		raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc
	except Exception as exc:  # noqa: BLE001
		raise HTTPException(status_code=401, detail=f"Token validation failed: {exc}") from exc


def get_current_principal(authorization: str | None = Header(default=None)) -> dict[str, Any]:
	token = _extract_bearer_token(authorization)

	# 段階移行のため、内部連携向け shared secret を一時的に許容する。
	if token == SHARED_SECRET:
		return {"auth_type": "internal", "sub": "internal-service"}

	claims = _decode_keycloak_token(token)
	return {"auth_type": "user", **claims}