"""async def エンドポイント内の同期処理（DB アクセス・bcrypt）が、イベントループ外のスレッドで実行されることのテスト（#120）"""

import threading

import pytest
from fastapi import HTTPException

from app.api.v1 import join as join_api
from app.api.v1 import student as student_api
from app.api.v1 import survey as survey_api
from app.db.student_repository import OTPVerificationResult

PRINCIPAL = {"discord_id": "test-discord-id"}


class ThreadRecorder:
	"""同期関数の代わりに呼ばれ、呼び出し元のスレッド ID を記録する"""

	def __init__(self):
		self.calls: dict[str, int] = {}

	def fake(self, name: str, return_value=None, error: Exception | None = None):
		def _fake(*args, **kwargs):
			self.calls[name] = threading.get_ident()
			if error is not None:
				raise error
			return return_value
		return _fake

	def assert_offloaded(self, caller_thread_id: int, names: list[str]) -> None:
		assert sorted(self.calls) == sorted(names)
		for name in names:
			assert self.calls[name] != caller_thread_id, f"{name} must run outside the event loop thread"


class FakeBrevoClient:
	async def send_otp_email(self, **kwargs):
		return {"status": "success"}

	async def send_invite_email(self, **kwargs):
		return {"status": "success"}


@pytest.fixture
def recorder():
	return ThreadRecorder()


@pytest.fixture
def eligible_student(monkeypatch):
	"""入会資格（pre_member かつ支払済み）を満たす状態にする"""
	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: True)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: True)


def _join_request() -> join_api.JoinRequestCreate:
	return join_api.JoinRequestCreate(
		email="test@example.com",
		confirm_email="test@example.com",
		name="テスト 太郎",
		form_type="contact",
	)


def _profile_request() -> student_api.StudentProfileRequest:
	return student_api.StudentProfileRequest(
		student_number="1A234567",
		name="テスト 太郎",
		furigana="テスト タロウ",
		department="テスト学部",
		gender=None,
		phone="09000000000",
	)


# ==================== join ====================

@pytest.mark.asyncio
async def test_join_request_offloads_db_and_hash(monkeypatch, recorder):
	join_request = {
		"id": "request-id",
		"email": "test@example.com",
		"name": "テスト 太郎",
		"form_type": "contact",
		"status": "pending",
	}
	monkeypatch.setattr(join_api.repository, "create_join_request", recorder.fake("create_join_request", join_request))
	monkeypatch.setattr(join_api, "hash_otp_code", recorder.fake("hash_otp_code", "hashed"))
	monkeypatch.setattr(join_api.repository, "create_otp_code", recorder.fake("create_otp_code"))
	monkeypatch.setattr(join_api, "BrevoClient", FakeBrevoClient)

	response = await join_api.request_otp(_join_request())

	assert response.id == "request-id"
	recorder.assert_offloaded(
		threading.get_ident(),
		["create_join_request", "hash_otp_code", "create_otp_code"],
	)


@pytest.mark.asyncio
async def test_join_request_returns_409_when_duplicated(monkeypatch, recorder):
	monkeypatch.setattr(
		join_api.repository,
		"create_join_request",
		recorder.fake("create_join_request", error=ValueError("duplicated")),
	)

	with pytest.raises(HTTPException) as error:
		await join_api.request_otp(_join_request())

	assert error.value.status_code == 409
	recorder.assert_offloaded(threading.get_ident(), ["create_join_request"])


@pytest.mark.asyncio
async def test_join_verify_offloads_join_request_lookup(monkeypatch, recorder):
	async def fake_create_channel_invite(*args, **kwargs):
		return {"code": "invite-code"}

	monkeypatch.setenv("DISCORD_TOKEN", "dummy-token")
	monkeypatch.setenv("DISCORD_INVITE_CHANNEL_ID", "dummy-channel")
	monkeypatch.setattr(join_api.repository, "verify_otp", recorder.fake("verify_otp"))
	monkeypatch.setattr(join_api, "create_channel_invite", fake_create_channel_invite)
	monkeypatch.setattr(
		join_api.repository,
		"get_join_request",
		recorder.fake("get_join_request", {"email": "test@example.com", "name": "テスト 太郎", "form_type": "contact"}),
	)
	monkeypatch.setattr(join_api, "BrevoClient", FakeBrevoClient)

	response = await join_api.verify_otp(
		join_api.JoinVerifyRequest(join_request_id="request-id", otp_code="000000")
	)

	assert response.discord_invite_url == "https://discord.gg/invite-code"
	recorder.assert_offloaded(threading.get_ident(), ["verify_otp", "get_join_request"])


# ==================== student ====================

@pytest.mark.asyncio
async def test_student_send_otp_offloads_otp_record_creation(monkeypatch, recorder, eligible_student):
	monkeypatch.setattr(student_api, "hash_otp_code", lambda code: "hashed")
	monkeypatch.setattr(student_api.student_repository, "create_otp_record", recorder.fake("create_otp_record"))
	monkeypatch.setattr(student_api, "BrevoClient", FakeBrevoClient)

	response = await student_api.send_otp(
		student_api.SendOTPRequest(student_number="1A234567", name="テスト 太郎"),
		principal=PRINCIPAL,
	)

	assert response.email_aoyama == "aa234567@aoyama.ac.jp"
	recorder.assert_offloaded(threading.get_ident(), ["create_otp_record"])


@pytest.mark.asyncio
async def test_student_verify_otp_offloads_role_updates(monkeypatch, recorder, eligible_student):
	monkeypatch.setenv("MEMBER_ROLE_IDS", "member-role")
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", "pre-member-role")
	monkeypatch.setattr(
		student_api.student_repository,
		"verify_otp_transactional",
		lambda discord_id, code: OTPVerificationResult.VERIFIED,
	)
	monkeypatch.setattr(student_api, "add_user_to_role", recorder.fake("add_user_to_role"))
	monkeypatch.setattr(student_api, "remove_user_from_role", recorder.fake("remove_user_from_role"))

	response = await student_api.verify_otp(
		student_api.VerifyOTPRequest(code="000000"),
		principal=PRINCIPAL,
	)

	assert response.verified is True
	recorder.assert_offloaded(threading.get_ident(), ["add_user_to_role", "remove_user_from_role"])


@pytest.mark.asyncio
async def test_student_create_profile_offloads_db_access(monkeypatch, recorder, eligible_student):
	monkeypatch.delenv("DISCORD_TOKEN", raising=False)
	monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
	monkeypatch.setattr(
		student_api.student_repository,
		"get_latest_verified_otp",
		recorder.fake("get_latest_verified_otp", {"verified": True}),
	)
	monkeypatch.setattr(
		student_api.student_repository,
		"upsert_student_profile_and_promote",
		recorder.fake("upsert_student_profile_and_promote", "prof_test"),
	)

	response = await student_api.create_student_profile(
		_profile_request(),
		principal={**PRINCIPAL, "app_role": "pre_member"},
	)

	assert response.profile_id == "prof_test"
	recorder.assert_offloaded(
		threading.get_ident(),
		["get_latest_verified_otp", "upsert_student_profile_and_promote"],
	)


# ==================== survey ====================

@pytest.mark.asyncio
async def test_survey_offloads_db_access(monkeypatch, recorder):
	monkeypatch.setattr(
		survey_api.repository,
		"get_student_profile",
		recorder.fake("get_student_profile", {"id": "prof_test", "student_number": "1A234567"}),
	)
	monkeypatch.setattr(
		survey_api.repository,
		"save_member_survey_response",
		recorder.fake("save_member_survey_response", {"id": 1, "created_at": None}),
	)

	response = await survey_api.submit_survey(survey_api.SurveyRequest(), principal=PRINCIPAL)

	assert response.id == 1
	recorder.assert_offloaded(
		threading.get_ident(),
		["get_student_profile", "save_member_survey_response"],
	)


@pytest.mark.asyncio
async def test_survey_returns_500_when_save_fails(monkeypatch, recorder):
	monkeypatch.setattr(survey_api.repository, "get_student_profile", recorder.fake("get_student_profile"))
	monkeypatch.setattr(
		survey_api.repository,
		"save_member_survey_response",
		recorder.fake("save_member_survey_response", error=RuntimeError("db error")),
	)

	with pytest.raises(HTTPException) as error:
		await survey_api.submit_survey(survey_api.SurveyRequest(), principal=PRINCIPAL)

	assert error.value.status_code == 500
	recorder.assert_offloaded(
		threading.get_ident(),
		["get_student_profile", "save_member_survey_response"],
	)
