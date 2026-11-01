"""役割: 内部サービス間通信用シークレット（SHARED_SECRET）の検証

SHARED_SECRET による Bearer トークン認証は admin 相当の権限を与えるため、
起動時に値の強度を検証し、照合は定数時間比較で行う。
"""

from __future__ import annotations

import hmac
import logging
import os

from fastapi import HTTPException

from app.core.config import MIN_SHARED_SECRET_LENGTH

logger = logging.getLogger(__name__)

SHARED_SECRET = os.getenv("SHARED_SECRET", "")


def validate_shared_secret(env: str) -> None:
	"""SHARED_SECRET が未設定または短すぎる場合、本番では起動を止め、それ以外では警告する。

	メッセージには秘密情報を含めないため、値や長さは出さない。
	"""
	if not SHARED_SECRET:
		reason = "SHARED_SECRET is not set"
	elif len(SHARED_SECRET) < MIN_SHARED_SECRET_LENGTH:
		reason = f"SHARED_SECRET must be at least {MIN_SHARED_SECRET_LENGTH} characters"
	else:
		return

	if env == "production":
		raise RuntimeError(reason)
	logger.warning("%s (allowed only outside production)", reason)


def is_internal_token(token: str | None) -> bool:
	"""トークンが SHARED_SECRET と一致するか。SHARED_SECRET が未設定なら常に False。"""
	if not SHARED_SECRET or not token:
		return False
	return hmac.compare_digest(token.encode(), SHARED_SECRET.encode())


def verify_internal_authorization(authorization: str | None) -> None:
	"""Authorization ヘッダーが `Bearer <SHARED_SECRET>` でなければ 401 を返す。"""
	scheme, _, token = (authorization or "").partition(" ")
	if scheme.lower() != "bearer" or not is_internal_token(token):
		raise HTTPException(status_code=401, detail="Unauthorized")
