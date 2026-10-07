"""OTP 検証時の行ロック待ちに上限（lock_timeout）を設けることのテスト（#126）

実DBには接続せず、カーソルを模したモックで実行される SQL を検証する。
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from psycopg2 import errors as pg_errors

from app.api.v1 import join as join_api
from app.api.v1 import student as student_api
from app.core.config import OTP_LOCK_TIMEOUT_MS
from app.core.exceptions import OTPVerificationBusyError
from app.db import otp_repository, student_repository


BUSY_MESSAGE = "同じ認証コードの確認が同時に行われています。しばらく待ってから再度お試しください。"


class _FakeCursor:
	def __init__(self, conn):
		self._conn = conn

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def execute(self, sql, params=None):
		normalized = " ".join(sql.split())
		self._conn.executed.append((normalized, params))
		if normalized.endswith("FOR UPDATE") and self._conn.lock_error is not None:
			raise self._conn.lock_error

	def fetchone(self):
		# 対象の OTP が無い場合の経路で検証を終える
		return None


class _FakeConnection:
	def __init__(self, lock_error: Exception | None = None):
		self.lock_error = lock_error
		self.executed: list[tuple[str, object]] = []
		self.rolled_back = False

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, tb):
		# _PooledConnection と同様に例外時はロールバックする
		if exc_type is not None:
			self.rolled_back = True
		return False

	def cursor(self):
		return _FakeCursor(self)

	def commit(self):
		pass


VERIFY_CASES = [
	pytest.param(otp_repository, lambda: otp_repository.verify_otp("request-id", "000000"), id="join"),
	pytest.param(
		student_repository,
		lambda: student_repository.verify_otp_transactional("test-discord-id", "000000"),
		id="student",
	),
]


@pytest.mark.parametrize(("module", "verify"), VERIFY_CASES)
def test_sets_lock_timeout_before_select_for_update(monkeypatch, module, verify):
	conn = _FakeConnection()
	monkeypatch.setattr(module, "_connect", lambda: conn)

	# 対象の OTP が無いので ValueError で終わる（ロックの取り方だけを確認する）
	with pytest.raises(ValueError):
		verify()

	statements = [sql for sql, _ in conn.executed]
	assert statements[0] == "SET LOCAL lock_timeout = %s"
	assert conn.executed[0][1] == (f"{OTP_LOCK_TIMEOUT_MS}ms",)
	assert statements[1].startswith("SELECT") and statements[1].endswith("FOR UPDATE")


@pytest.mark.parametrize(("module", "verify"), VERIFY_CASES)
def test_raises_busy_error_when_lock_wait_times_out(monkeypatch, module, verify):
	conn = _FakeConnection(lock_error=pg_errors.LockNotAvailable("canceling statement due to lock timeout"))
	monkeypatch.setattr(module, "_connect", lambda: conn)

	with pytest.raises(OTPVerificationBusyError) as error:
		verify()

	# 利用者向けの文言は例外クラスの既定メッセージを使う
	assert str(error.value) == BUSY_MESSAGE
	assert conn.rolled_back is True


@pytest.mark.asyncio
async def test_join_verify_returns_409_when_busy(monkeypatch):
	def busy(**kwargs):
		raise OTPVerificationBusyError()

	monkeypatch.setattr(join_api.repository, "verify_otp", busy)

	with pytest.raises(HTTPException) as error:
		await join_api.verify_otp(join_api.JoinVerifyRequest(join_request_id="request-id", otp_code="000000"))

	assert error.value.status_code == 409
	assert error.value.detail == BUSY_MESSAGE


@pytest.mark.asyncio
async def test_student_verify_returns_409_when_busy(monkeypatch):
	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: True)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: True)

	def busy(discord_id, code):
		raise OTPVerificationBusyError()

	monkeypatch.setattr(student_api.student_repository, "verify_otp_transactional", busy)

	with pytest.raises(HTTPException) as error:
		await student_api.verify_otp(
			student_api.VerifyOTPRequest(code="000000"),
			principal={"discord_id": "test-discord-id"},
		)

	assert error.value.status_code == 409
	assert error.value.detail == BUSY_MESSAGE
