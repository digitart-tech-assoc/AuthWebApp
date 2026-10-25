"""メンバー単位のロールの付け外し（self-batch・入会・プロフィール・pre-member 登録）の監査ログのテスト"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main
from app.api.v1 import members as members_api
from app.api.v1 import roles as roles_api
from app.api.v1 import student as student_api
from app.db import audit_repository, guild_repository, membership_repository
from app.db.audit_repository import AuditContext
from tests.fake_role_db import AuditInsertError, FakeRoleDB

AUDIT = AuditContext(request_id="req-1", actor_sub="sub-1", actor_discord_id="500", operation="self_batch")


@pytest.fixture
def db(monkeypatch):
	fake = FakeRoleDB()
	for module in (audit_repository, guild_repository, membership_repository):
		monkeypatch.setattr(module, "_connect", fake.connect)
	return fake


def _summary(db):
	return [(log["system"], log["target_type"], log["target_id"], log["action"], log["after"]) for log in db.audit_logs]


# --- リポジトリ ---

def test_batch_update_records_only_actual_changes(db):
	db.assign("11", "500")
	db.assign("12", "500")

	# 11 は既に付いている（ON CONFLICT DO NOTHING）、13 は付いていない（DELETE しても変わらない）
	guild_repository.batch_update_user_roles("500", ["11", "14"], ["12", "13"], AUDIT)

	assert _summary(db) == [("db", "member_roles", "500", "update", {"added": ["14"], "removed": ["12"]})]


def test_batch_update_without_actual_change_records_nothing(db):
	db.assign("11", "500")

	guild_repository.batch_update_user_roles("500", ["11"], ["12"], AUDIT)

	assert db.audit_logs == []


def test_batch_update_rolls_back_when_audit_insert_fails(db):
	db.fail_audit_insert = True

	with pytest.raises(AuditInsertError):
		guild_repository.batch_update_user_roles("500", ["11"], [], AUDIT)

	assert db.members_of("11") == set()


def test_add_user_to_role_records_only_when_inserted(db):
	guild_repository.add_user_to_role("500", "11", AUDIT)
	guild_repository.add_user_to_role("500", "11", AUDIT)

	assert _summary(db) == [("db", "member_roles", "500", "update", {"added": ["11"], "removed": []})]


def test_remove_user_from_role_records_only_when_deleted(db):
	db.assign("11", "500")

	guild_repository.remove_user_from_role("500", "11", AUDIT)
	guild_repository.remove_user_from_role("500", "11", AUDIT)

	assert _summary(db) == [("db", "member_roles", "500", "update", {"added": [], "removed": ["11"]})]


def test_register_pre_member_records_as_internal_service(db, monkeypatch):
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", "pre-role")
	audit = audit_repository.internal_audit_context("pre_member_register")

	result = membership_repository.register_pre_member("500", "bot", audit)

	assert result["role_assignment_created"] is True
	log = db.audit_logs[0]
	assert (log["operation"], log["actor_sub"], log["actor_discord_id"]) == ("pre_member_register", "internal-service", None)
	assert log["after"] == {"added": ["pre-role"], "removed": []}


def test_register_pre_member_without_new_assignment_records_nothing(db, monkeypatch):
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", "pre-role")
	db.assign("pre-role", "500")

	membership_repository.register_pre_member("500", "bot", audit_repository.internal_audit_context("pre_member_register"))

	assert db.audit_logs == []


# --- self-batch ---

MANIFEST = {
	"roles": [
		{"role_id": "11", "name": "A", "category_id": "cat-open", "permissions": 0},
		{"role_id": "12", "name": "B", "category_id": "cat-open", "permissions": 0},
	],
	"categories": [{"id": "cat-open", "name": "趣味", "is_restricted": False}],
}
DISCORD_ROLES = [
	{"role_id": "11", "position": 1, "managed": False},
	{"role_id": "12", "position": 2, "managed": False},
	{"role_id": "role-bot", "position": 10, "managed": True},
]


async def _self_batch(db_side_effect=None, set_side_effect=None):
	with patch.object(roles_api, "_get_token", return_value="token"), \
		patch.object(roles_api, "fetch_manifest", return_value=MANIFEST), \
		patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
		patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": ["12"]}), \
		patch.object(roles_api, "fetch_bot_guild_member", new_callable=AsyncMock, return_value={"role_ids": ["role-bot"]}), \
		patch.object(roles_api, "fetch_role_ids_with_channel_permissions", new_callable=AsyncMock, return_value=set()), \
		patch.object(roles_api, "set_member_roles", new_callable=AsyncMock, side_effect=set_side_effect), \
		patch.object(roles_api, "batch_update_user_roles", side_effect=db_side_effect) as batch:
		result = await roles_api.self_batch_roles(
			roles_api.SelfBatchPayload(roles_to_add=["11"], roles_to_remove=["12"]),
			{"sub": "sub-1", "discord_id": "500", "app_role": "member"},
			audit=AuditContext("req-1", "sub-1", "500"),
		)
	return result, batch


@pytest.mark.asyncio
async def test_self_batch_records_discord_change_and_passes_audit_to_db(db):
	result, batch = await _self_batch()

	assert result["ok"] is True
	assert _summary(db) == [("discord", "member_roles", "500", "update", {"added": ["11"], "removed": ["12"]})]
	assert db.audit_logs[0]["operation"] == "self_batch"
	assert batch.call_args.args[-1] == AuditContext("req-1", "sub-1", "500", "self_batch")


@pytest.mark.asyncio
async def test_self_batch_records_rollback_when_db_update_fails(db):
	with pytest.raises(HTTPException) as error:
		await _self_batch(db_side_effect=RuntimeError("db down"))

	assert error.value.status_code == 500
	assert _summary(db) == [
		("discord", "member_roles", "500", "update", {"added": ["11"], "removed": ["12"]}),
		("discord", "member_roles", "500", "rollback", {"added": ["12"], "removed": ["11"]}),
	]


@pytest.mark.asyncio
async def test_self_batch_failed_discord_update_is_not_recorded(db):
	with pytest.raises(HTTPException):
		await _self_batch(set_side_effect=RuntimeError("discord down"))

	assert db.audit_logs == []


# --- 入会（OTP 検証）・プロフィール ---

@pytest.mark.asyncio
async def test_verify_otp_passes_audit_and_keeps_success_when_recording_fails(monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", "member-role")
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", "pre-role")
	monkeypatch.setattr(student_api, "_ensure_registration_eligible", AsyncMock())
	monkeypatch.setattr(
		student_api.student_repository, "verify_otp_transactional",
		lambda discord_id, code: student_api.student_repository.OTPVerificationResult.VERIFIED,
	)
	calls = []

	def _add(user_id, role_id, audit):
		calls.append(audit)
		raise AuditInsertError("audit insert failed")

	monkeypatch.setattr(student_api, "add_user_to_role", _add)
	monkeypatch.setattr(student_api, "remove_user_from_role", lambda *args: None)

	response = await student_api.verify_otp(
		student_api.VerifyOTPRequest(code="000000"),
		principal={"sub": "sub-1", "discord_id": "500"},
		audit=AuditContext("req-1", "sub-1", "500"),
	)

	# 記録に失敗した場合も、OTP 検証は成功として返す（従来どおり）
	assert response.verified is True
	assert calls == [AuditContext("req-1", "sub-1", "500", "join_otp_verify")]


@pytest.mark.asyncio
async def test_create_profile_records_each_discord_role_assignment(db, monkeypatch):
	monkeypatch.setenv("DISCORD_TOKEN", "dummy-token")
	monkeypatch.setenv("DISCORD_GUILD_ID", "dummy-guild")
	monkeypatch.setenv("MEMBER_ROLE_IDS", "m1,m2")
	promote_calls = []
	monkeypatch.setattr(
		student_api.student_repository, "upsert_student_profile_and_promote",
		lambda **kwargs: promote_calls.append(kwargs) or "prof_test",
	)
	add_role = AsyncMock(side_effect=[None, RuntimeError("discord down")])
	monkeypatch.setattr(student_api, "add_role_to_member", add_role)

	await student_api.create_student_profile(
		student_api.StudentProfileRequest(
			student_number="1A234567", name="テスト 太郎", furigana="テスト タロウ",
			department="テスト学部", phone="09000000000",
		),
		principal={"sub": "sub-1", "discord_id": "500", "app_role": "member"},
		audit=AuditContext("req-1", "sub-1", "500"),
	)

	assert promote_calls[0]["audit"] == AuditContext("req-1", "sub-1", "500", "student_profile")
	# 成功した付与だけを記録する
	assert _summary(db) == [("discord", "member_roles", "500", "update", {"added": ["m1"], "removed": []})]


# --- pre-member 登録（内部エンドポイント） ---

def test_pre_member_register_endpoint_uses_internal_audit_context(monkeypatch):
	monkeypatch.setattr(members_api, "SHARED_SECRET", "test-secret")
	calls = []
	monkeypatch.setattr(
		members_api, "register_pre_member",
		lambda discord_id, source, audit: calls.append(audit) or {"created": True},
	)

	res = TestClient(main.app).post(
		"/api/v1/members/pre_member/register",
		json={"discord_id": "500", "source": "bot"},
		headers={"Authorization": "Bearer test-secret"},
	)

	assert res.status_code == 200
	assert calls[0].actor_sub == "internal-service"
	assert calls[0].actor_discord_id is None
	assert calls[0].operation == "pre_member_register"
