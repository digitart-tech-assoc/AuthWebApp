import threading

import pytest
from fastapi import HTTPException

from app.api.v1 import join as join_api
from app.api.v1 import student as student_api
from app.core.exceptions import OTPTooManyAttemptsError
from app.db.student_repository import OTPVerificationResult
from tests.request_factory import make_request


@pytest.fixture
def eligible_student(monkeypatch):
	"""入会資格（pre_member かつ支払済み）を満たす状態にする"""
	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: True)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: True)


@pytest.mark.asyncio
async def test_verified_student_otp_does_not_repeat_role_updates(monkeypatch, eligible_student):
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
async def test_student_otp_limit_uses_typed_exception_for_429(monkeypatch, eligible_student):
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

@pytest.mark.asyncio
@pytest.mark.parametrize(
	("form_type", "metadata"),
	[
		("prospective-student", {"year": 2026}),
		("aoyama-student", {"student_id": "1A234567"}),
	],
)
async def test_join_request_passes_form_metadata_to_repository(monkeypatch, form_type, metadata):
	"""フォーム固有の項目（入学予定年度・学生番号）が join_requests.metadata に保存される"""
	saved = {}

	def fake_create_join_request(**kwargs):
		saved.update(kwargs)
		return {
			"id": "request-id",
			"email": kwargs["email"],
			"name": kwargs["name"],
			"form_type": kwargs["form_type"],
			"status": "pending",
		}

	class FakeBrevoClient:
		async def send_otp_email(self, **kwargs):
			return {"status": "success"}

	monkeypatch.setattr(join_api.repository, "is_prospective_form_open", lambda: True)
	monkeypatch.setattr(join_api.repository, "create_join_request", fake_create_join_request)
	monkeypatch.setattr(join_api.repository, "create_otp_code", lambda **kwargs: None)
	monkeypatch.setattr(join_api, "hash_otp_code", lambda code: "hashed")
	monkeypatch.setattr(join_api, "BrevoClient", FakeBrevoClient)

	await join_api.request_otp(
		join_api.JoinRequestCreate(
			email="applicant@example.com",
			confirm_email="applicant@example.com",
			name="テスト 太郎",
			form_type=form_type,
			metadata=metadata,
		),
		make_request(),
	)

	assert saved["form_type"] == form_type
	assert saved["metadata"] == metadata


@pytest.mark.asyncio
@pytest.mark.parametrize(
	"metadata",
	[None, {}, {"year": None}, {"year": "2026"}, {"year": True}, {"year": 2026.5}],
)
async def test_prospective_join_request_requires_integer_year(monkeypatch, metadata):
	"""入学見込みフォームは metadata.year（整数）がなければ申請を作らずに 400 を返す"""
	created = []

	monkeypatch.setattr(join_api.repository, "is_prospective_form_open", lambda: True)
	monkeypatch.setattr(
		join_api.repository, "create_join_request", lambda **kwargs: created.append(kwargs)
	)

	with pytest.raises(HTTPException) as error:
		await join_api.request_otp(
			join_api.JoinRequestCreate(
				email="applicant@example.com",
				confirm_email="applicant@example.com",
				name="テスト 太郎",
				form_type="prospective-student",
				metadata=metadata,
			),
			make_request(),
		)

	assert error.value.status_code == 400
	assert created == []
