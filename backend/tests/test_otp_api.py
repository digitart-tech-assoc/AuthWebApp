import threading

import pytest
from fastapi import HTTPException

from app.api.v1 import join as join_api
from app.api.v1 import student as student_api
from app.core.exceptions import OTPTooManyAttemptsError
from app.db.student_repository import OTPVerificationResult


@pytest.mark.asyncio
async def test_verified_student_otp_does_not_repeat_role_updates(monkeypatch):
	monkeypatch.setattr(
		student_api.student_repository,
		"verify_otp_transactional",
		lambda discord_id, code: OTPVerificationResult.ALREADY_VERIFIED,
	)
	monkeypatch.setenv("MEMBER_ROLE_IDS", "member-role")
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", "pre-member-role")
	monkeypatch.setattr(
		student_api,
		"add_user_to_role",
		lambda *args: pytest.fail("already verified OTP must not add roles"),
	)
	monkeypatch.setattr(
		student_api,
		"remove_user_from_role",
		lambda *args: pytest.fail("already verified OTP must not remove roles"),
	)

	response = await student_api.verify_otp(
		student_api.VerifyOTPRequest(code="000000"),
		principal={"discord_id": "test-discord-id"},
	)

	assert response.message == "OTP already verified"


@pytest.mark.asyncio
async def test_student_otp_limit_uses_typed_exception_for_429(monkeypatch):
	def reject_verification(discord_id, code):
		raise OTPTooManyAttemptsError("limit reached")

	monkeypatch.setattr(
		student_api.student_repository,
		"verify_otp_transactional",
		reject_verification,
	)

	with pytest.raises(HTTPException) as error:
		await student_api.verify_otp(
			student_api.VerifyOTPRequest(code="000000"),
			principal={"discord_id": "test-discord-id"},
		)

	assert error.value.status_code == 429


@pytest.mark.asyncio
async def test_join_otp_limit_uses_thread_and_returns_429(monkeypatch):
	caller_thread_id = threading.get_ident()
	verification_thread_ids = []

	def reject_verification(**kwargs):
		verification_thread_ids.append(threading.get_ident())
		raise OTPTooManyAttemptsError("limit reached")

	monkeypatch.setattr(join_api.repository, "verify_otp", reject_verification)

	with pytest.raises(HTTPException) as error:
		await join_api.verify_otp(
			join_api.JoinVerifyRequest(join_request_id="request-id", otp_code="000000")
		)

	assert error.value.status_code == 429
	assert verification_thread_ids
	assert verification_thread_ids[0] != caller_thread_id