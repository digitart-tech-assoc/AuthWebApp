"""エラーの出力規約のテスト（docs/logging-and-errors.md）

- API のエラーレスポンス（HTTPException の detail・push の errors 等）に例外メッセージを含めない（§3.2）
- 個人情報を扱う処理の例外は、メッセージを除いてログに出す（§3.1）
- 認証情報（JWT 等）をログに出さない（§1.2）
"""

import ast
import logging
from pathlib import Path
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import HTTPException

from app.api.v1 import join as join_api
from app.core import auth
from app.core.errors import describe_exception, log_exception_without_message
from app.services.discord_client import DiscordAPIError

APP_DIR = Path(__file__).resolve().parents[1] / "app"
# レスポンスを組み立てる API 層
API_DIR = APP_DIR / "api"

# 例外を受け取ってもメッセージをレスポンスに出さない（ログ出力・メッセージを除いて表す）関数
SAFE_CALLS = {"describe_exception", "log_exception_without_message", "_log_push_error", "redact_snowflakes", "type", "print"}
# 自前の例外で、メッセージが固定文言のもの（app/core/exceptions.py）。detail にそのまま使ってよい
FIXED_MESSAGE_EXCEPTIONS = {"OTPVerificationBusyError", "RegistrationNotEligibleError"}


def _call_name(node: ast.Call) -> str | None:
	if isinstance(node.func, ast.Name):
		return node.func.id
	if isinstance(node.func, ast.Attribute):
		if isinstance(node.func.value, ast.Name) and node.func.value.id == "logger":
			return "logger"
		return node.func.attr
	return None


def _message_uses(handler: ast.ExceptHandler) -> list[int]:
	"""except 節の中で、受け取った例外を文字列化している箇所（ログ出力を除く）の行番号を返す。"""
	if isinstance(handler.type, ast.Name) and handler.type.id in FIXED_MESSAGE_EXCEPTIONS:
		return []
	parents: dict[ast.AST, ast.AST] = {}
	for stmt in handler.body:
		for parent in ast.walk(stmt):
			for child in ast.iter_child_nodes(parent):
				parents[child] = parent

	def is_safe(node: ast.AST) -> bool:
		current = parents.get(node)
		while current is not None:
			if isinstance(current, ast.Call) and _call_name(current) in SAFE_CALLS | {"logger"}:
				return True
			current = parents.get(current)
		return False

	lines = []
	for stmt in handler.body:
		for node in ast.walk(stmt):
			if not (isinstance(node, ast.Name) and node.id == handler.name):
				continue
			parent = parents.get(node)
			stringified = (
				isinstance(parent, ast.FormattedValue)
				or (isinstance(parent, ast.Call) and _call_name(parent) == "str")
				or (isinstance(parent, ast.keyword) and parent.arg == "detail")
			)
			if stringified and not is_safe(node):
				lines.append(node.lineno)
	return lines


def test_exception_messages_are_not_put_into_responses():
	violations = []
	for path in sorted(API_DIR.rglob("*.py")):
		relative = path.relative_to(APP_DIR.parent).as_posix()
		tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
		for node in ast.walk(tree):
			if isinstance(node, ast.ExceptHandler) and node.name:
				violations.extend(f"{relative}:{line}" for line in _message_uses(node))

	assert violations == []


def test_describe_exception_omits_message():
	assert describe_exception(RuntimeError("applicant@example.com")) == "RuntimeError"
	assert describe_exception(DiscordAPIError("body with details", 500)) == "DiscordAPIError HTTP 500"


def test_log_exception_without_message_keeps_stack_but_not_message(caplog):
	logger = logging.getLogger("test_error_output")
	message = "applicant" + "@example.com"
	try:
		raise ValueError(message)
	except ValueError as exc:
		with caplog.at_level(logging.ERROR, logger=logger.name):
			log_exception_without_message(logger, "save something", exc)

	assert "save something failed (ValueError)" in caplog.text
	assert "test_log_exception_without_message_keeps_stack_but_not_message" in caplog.text
	assert "applicant@example.com" not in caplog.text
	assert caplog.records[-1].exc_info is None


@pytest.mark.asyncio
async def test_join_request_conflict_does_not_return_email(monkeypatch):
	email = "applicant@example.com"

	def _raise_conflict(**kwargs):
		raise ValueError(f"Email {email} already registered")

	monkeypatch.setattr(join_api.repository, "create_join_request", _raise_conflict)

	with pytest.raises(HTTPException) as error:
		await join_api.request_otp(
			join_api.JoinRequestCreate(email=email, confirm_email=email, name="テスト 太郎", form_type="other")
		)

	assert error.value.status_code == 409
	assert email not in str(error.value.detail)


@pytest.mark.asyncio
async def test_join_request_send_failure_does_not_return_brevo_body(monkeypatch):
	email = "applicant@example.com"
	monkeypatch.setattr(join_api.repository, "create_join_request", lambda **kwargs: {"id": "jr_1"})
	monkeypatch.setattr(join_api.repository, "create_otp_code", lambda **kwargs: None)
	monkeypatch.setattr(join_api, "hash_otp_code", lambda code: "hashed")

	class FakeBrevoClient:
		send_otp_email = AsyncMock(return_value={"status": "failed", "error": f"400 invalid recipient {email}"})

	monkeypatch.setattr(join_api, "BrevoClient", FakeBrevoClient)

	with pytest.raises(HTTPException) as error:
		await join_api.request_otp(
			join_api.JoinRequestCreate(email=email, confirm_email=email, name="テスト 太郎", form_type="other")
		)

	# 送信失敗の 500 が、汎用の except で包み直されずにそのまま返ること
	assert error.value.status_code == 500
	assert error.value.detail == "Failed to send OTP email"


def test_invalid_issuer_does_not_log_token(monkeypatch, caplog):
	token = "header.payload-with-claims.signature"

	def _raise_invalid_issuer(*args, **kwargs):
		raise jwt.InvalidIssuerError("issuer mismatch")

	monkeypatch.setattr(auth, "SUPABASE_JWT_SECRET", "secret", raising=False)
	monkeypatch.setattr(auth.jwt, "get_unverified_header", lambda _token: {"alg": "HS256"})
	monkeypatch.setattr(auth.jwt, "decode", _raise_invalid_issuer)

	with caplog.at_level(logging.DEBUG):
		with pytest.raises(HTTPException) as error:
			auth._decode_supabase_token(token)

	assert error.value.status_code == 401
	assert token not in caplog.text
