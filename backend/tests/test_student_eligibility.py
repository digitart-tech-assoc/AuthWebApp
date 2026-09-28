"""学生入会フローの入会資格（pre_member かつ支払済み）サーバーサイド検証のテスト"""

import pytest
from fastapi import HTTPException

from app.api.v1 import student as student_api

INELIGIBLE_CASES = [
	pytest.param(False, True, id="not-pre-member"),
	pytest.param(True, False, id="not-paid"),
	pytest.param(False, False, id="neither"),
]

PRINCIPAL = {"discord_id": "test-discord-id"}


def _set_eligibility(monkeypatch, is_pre_member: bool, is_paid: bool) -> None:
	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: is_pre_member)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: is_paid)


def _forbid(name: str):
	def _fail(*args, **kwargs):
		pytest.fail(f"{name} must not be called for ineligible users")
	return _fail


def _profile_request() -> student_api.StudentProfileRequest:
	return student_api.StudentProfileRequest(
		student_number="1A234567",
		name="テスト 太郎",
		furigana="テスト タロウ",
		department="テスト学部",
		gender=None,
		phone="09000000000",
	)


@pytest.mark.asyncio
@pytest.mark.parametrize(("is_pre_member", "is_paid"), INELIGIBLE_CASES)
async def test_send_otp_rejects_ineligible_user(monkeypatch, is_pre_member, is_paid):
	_set_eligibility(monkeypatch, is_pre_member, is_paid)
	monkeypatch.setattr(student_api.student_repository, "create_otp_record", _forbid("create_otp_record"))
	monkeypatch.setattr(student_api, "BrevoClient", _forbid("BrevoClient"))

	with pytest.raises(HTTPException) as error:
		await student_api.send_otp(
			student_api.SendOTPRequest(student_number="1A234567", name="テスト 太郎"),
			principal=PRINCIPAL,
		)

	assert error.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(("is_pre_member", "is_paid"), INELIGIBLE_CASES)
async def test_verify_otp_rejects_ineligible_user(monkeypatch, is_pre_member, is_paid):
	_set_eligibility(monkeypatch, is_pre_member, is_paid)
	monkeypatch.setattr(
		student_api.student_repository,
		"verify_otp_transactional",
		_forbid("verify_otp_transactional"),
	)
	monkeypatch.setattr(student_api, "add_user_to_role", _forbid("add_user_to_role"))

	with pytest.raises(HTTPException) as error:
		await student_api.verify_otp(
			student_api.VerifyOTPRequest(code="000000"),
			principal=PRINCIPAL,
		)

	assert error.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(("is_pre_member", "is_paid"), INELIGIBLE_CASES)
async def test_create_profile_rejects_ineligible_user(monkeypatch, is_pre_member, is_paid):
	_set_eligibility(monkeypatch, is_pre_member, is_paid)
	# OTP 検証済みでも入会資格がなければ本会員化させない
	monkeypatch.setattr(
		student_api.student_repository,
		"get_latest_verified_otp",
		lambda discord_id: {"verified": True},
	)
	monkeypatch.setattr(
		student_api.student_repository,
		"upsert_student_profile_and_promote",
		_forbid("upsert_student_profile_and_promote"),
	)

	with pytest.raises(HTTPException) as error:
		await student_api.create_student_profile(
			_profile_request(),
			principal={**PRINCIPAL, "app_role": "none"},
		)

	assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_create_profile_requires_verified_otp_for_eligible_user(monkeypatch):
	_set_eligibility(monkeypatch, True, True)
	monkeypatch.setattr(student_api.student_repository, "get_latest_verified_otp", lambda discord_id: None)
	monkeypatch.setattr(
		student_api.student_repository,
		"upsert_student_profile_and_promote",
		_forbid("upsert_student_profile_and_promote"),
	)

	with pytest.raises(HTTPException) as error:
		await student_api.create_student_profile(
			_profile_request(),
			principal={**PRINCIPAL, "app_role": "pre_member"},
		)

	assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_create_profile_promotes_eligible_verified_user(monkeypatch):
	_set_eligibility(monkeypatch, True, True)
	monkeypatch.delenv("DISCORD_TOKEN", raising=False)
	monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
	monkeypatch.setattr(
		student_api.student_repository,
		"get_latest_verified_otp",
		lambda discord_id: {"verified": True},
	)
	monkeypatch.setattr(
		student_api.student_repository,
		"upsert_student_profile_and_promote",
		lambda **kwargs: "prof_test",
	)

	response = await student_api.create_student_profile(
		_profile_request(),
		principal={**PRINCIPAL, "app_role": "pre_member"},
	)

	assert response.profile_id == "prof_test"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_role", ["member", "admin", "obog"])
async def test_create_profile_allows_registered_user_update(monkeypatch, app_role):
	# 既存会員のプロフィール更新は入会資格・OTP 検証の対象外
	monkeypatch.setattr(student_api, "_is_pre_member", _forbid("_is_pre_member"))
	monkeypatch.setattr(student_api, "_is_paid_invitation", _forbid("_is_paid_invitation"))
	monkeypatch.setattr(
		student_api.student_repository,
		"get_latest_verified_otp",
		_forbid("get_latest_verified_otp"),
	)
	monkeypatch.delenv("DISCORD_TOKEN", raising=False)
	monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
	monkeypatch.setattr(
		student_api.student_repository,
		"upsert_student_profile_and_promote",
		lambda **kwargs: "prof_test",
	)

	response = await student_api.create_student_profile(
		_profile_request(),
		principal={**PRINCIPAL, "app_role": app_role},
	)

	assert response.profile_id == "prof_test"
