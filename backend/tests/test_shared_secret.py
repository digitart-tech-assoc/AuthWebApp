"""SHARED_SECRET の検証と内部認証のテスト（#80）

- 本番では SHARED_SECRET が未設定または16文字未満なら起動しない
- 本番以外では警告のみで起動する
- メッセージに SHARED_SECRET の値を含めない
- SHARED_SECRET が未設定なら、どのトークンでも内部認証を通さない
"""

from __future__ import annotations

import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main
from app.core import shared_secret
from app.core.config import MIN_SHARED_SECRET_LENGTH

STRONG_SECRET = "s" * MIN_SHARED_SECRET_LENGTH
SHORT_SECRET = "short-value-1234"[: MIN_SHARED_SECRET_LENGTH - 1]


# --- 起動時の検証 ---

@pytest.mark.parametrize("value", ["", SHORT_SECRET])
def test_production_rejects_weak_secret(monkeypatch, value):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", value)

	with pytest.raises(RuntimeError) as exc_info:
		shared_secret.validate_shared_secret("production")

	if value:
		assert value not in str(exc_info.value)


def test_production_accepts_secret_of_minimum_length(monkeypatch):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", STRONG_SECRET)

	shared_secret.validate_shared_secret("production")


@pytest.mark.parametrize("env", ["development", "local", ""])
@pytest.mark.parametrize("value", ["", SHORT_SECRET])
def test_non_production_only_warns(monkeypatch, caplog, env, value):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", value)

	with caplog.at_level(logging.WARNING, logger=shared_secret.__name__):
		shared_secret.validate_shared_secret(env)

	assert "SHARED_SECRET" in caplog.text
	if value:
		assert value not in caplog.text


def test_non_production_does_not_warn_for_strong_secret(monkeypatch, caplog):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", STRONG_SECRET)

	with caplog.at_level(logging.WARNING, logger=shared_secret.__name__):
		shared_secret.validate_shared_secret("development")

	assert caplog.text == ""


def test_app_startup_fails_in_production_with_weak_secret(monkeypatch):
	monkeypatch.setattr(main, "_fastapi_env", "production")
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", SHORT_SECRET)

	with pytest.raises(RuntimeError):
		with TestClient(main.app):
			pass


# --- トークンの照合 ---

@pytest.mark.parametrize("token", [None, "", " ", "anything"])
def test_unset_secret_never_matches(monkeypatch, token):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", "")

	assert shared_secret.is_internal_token(token) is False


def test_matching_token(monkeypatch):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", STRONG_SECRET)

	assert shared_secret.is_internal_token(STRONG_SECRET) is True
	assert shared_secret.is_internal_token(STRONG_SECRET + "x") is False
	# 非 ASCII のトークンでも例外にならず不一致となる
	assert shared_secret.is_internal_token("ひみつ") is False


@pytest.mark.parametrize("authorization", [None, "", "Bearer", "Bearer ", f"Basic {STRONG_SECRET}", "Bearer wrong"])
def test_verify_internal_authorization_rejects(monkeypatch, authorization):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", STRONG_SECRET)

	with pytest.raises(HTTPException) as exc_info:
		shared_secret.verify_internal_authorization(authorization)

	assert exc_info.value.status_code == 401


def test_verify_internal_authorization_accepts(monkeypatch):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", STRONG_SECRET)

	shared_secret.verify_internal_authorization(f"Bearer {STRONG_SECRET}")


# --- 内部 API ---

@pytest.mark.parametrize("path", [
	"/api/v1/members/internal/lists",
	"/api/v1/members/pre_member/cleanup",
	"/api/v1/members/pre_member/register",
])
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer "}])
def test_internal_endpoints_reject_when_secret_unset(monkeypatch, path, headers):
	monkeypatch.setattr(shared_secret, "SHARED_SECRET", "")
	client = TestClient(main.app)

	if path.endswith("/internal/lists"):
		res = client.get(path, headers=headers)
	else:
		res = client.post(path, json={"discord_id": "500", "source": "bot"}, headers=headers)

	assert res.status_code == 401
