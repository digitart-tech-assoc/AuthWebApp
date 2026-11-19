"""会員種別を変える全経路の共通アドバイザリーロック・デッドロックリトライ・本会員化 403 のテスト（#264）

- D: 全対象経路（PUT / PATCH / add_to_member_list / 本会員化）で lock_memberships が最初の文として実行されること、
     会員種別のロールを含まない保存やプロフィール更新ではロックを取らないこと
- B: DeadlockDetected でトランザクション全体を 1 回だけリトライし、WARNING ログに関数名だけを出すこと。
     2 回目も失敗したら例外がそのまま送出され（API では 500）、何も反映されないこと
- 本会員化: pre_member に加えて member / sub_user の行または sub垢 の割当がある人は 403 でロールバックされること
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi import HTTPException
from psycopg2 import errors as pg_errors

from app.api.v1 import members as members_api
from app.api.v1 import student as student_api
from app.core.exceptions import RegistrationNotEligibleError
from app.db import (
	connection,
	guild_repository,
	manifest_repository,
	membership_assignment_repository,
	membership_repository,
	student_repository,
)
from app.db.audit_repository import AuditContext
from tests.fake_role_db import FakeRoleDB
from tests.request_factory import TEST_AUDIT

MEMBER, SUB, OBOG, PRE, ADMIN = "role-member", "role-sub", "role-obog", "role-pre", "role-admin"
GENERAL = "role-game"
USER = "100"
LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtext(%s))"


@pytest.fixture(autouse=True)
def role_env(monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", MEMBER)
	monkeypatch.setenv("SUB_USER_ROLE_IDS", SUB)
	monkeypatch.setenv("OBOG_ROLE_IDS", OBOG)
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", PRE)
	monkeypatch.setenv("ADMIN_ROLE_IDS", ADMIN)


@pytest.fixture
def db(monkeypatch) -> FakeRoleDB:
	fake = FakeRoleDB()
	monkeypatch.setattr(manifest_repository, "_connect", fake.connect)
	monkeypatch.setattr(guild_repository, "_connect", fake.connect)
	monkeypatch.setattr(membership_repository, "_connect", fake.connect)
	monkeypatch.setattr(student_repository, "_connect", fake.connect)
	return fake


def _role(role_id: str, **kwargs: Any) -> dict[str, Any]:
	row = {
		"role_id": role_id, "name": role_id, "color": "#000000", "hoist": False, "mentionable": False,
		"permissions": 0, "position": 1, "category_id": None, "is_our_bot": False,
	}
	row.update(kwargs)
	return row


def _promote(
	*,
	discord_id: str = USER,
	require_eligibility: bool = True,
	audit: AuditContext | None = None,
) -> student_repository.PromotionResult:
	return student_repository.upsert_student_profile_and_promote(
		profile_id="prof_1",
		discord_id=discord_id,
		student_number="1A234567",
		name="テスト 太郎",
		furigana="テスト タロウ",
		department="テスト学部",
		gender=None,
		phone="09000000000",
		email_aoyama="aa234567@aoyama.ac.jp",
		member_role_ids=[MEMBER],
		require_eligibility=require_eligibility,
		audit=audit,
		pre_member_role_id=PRE,
	)


def _inject_deadlock_on_sql(
	monkeypatch,
	db: FakeRoleDB,
	target_module: Any,
	trigger_substring: str,
	fail_times: int = 1,
) -> dict[str, int]:
	"""指定した SQL が実行されたタイミングで最初の fail_times 回だけ DeadlockDetected を送出する。"""
	state = {"failed": 0, "connects": 0}

	class _DeadlockingCursor:
		def __init__(self, inner):
			self._inner = inner

		def __enter__(self):
			self._inner.__enter__()
			return self

		def __exit__(self, *args):
			return self._inner.__exit__(*args)

		def __getattr__(self, name):
			return getattr(self._inner, name)

		def execute(self, sql: str, params=None):
			self._inner.execute(sql, params)
			normalized = " ".join(sql.split())
			if trigger_substring in normalized and state["failed"] < fail_times:
				state["failed"] += 1
				raise pg_errors.DeadlockDetected("deadlock detected")

	class _DeadlockingConn:
		def __init__(self, inner):
			self._inner = inner

		def __enter__(self):
			self._inner.__enter__()
			return self

		def __exit__(self, *args):
			return self._inner.__exit__(*args)

		def __getattr__(self, name):
			return getattr(self._inner, name)

		def cursor(self):
			return _DeadlockingCursor(self._inner.cursor())

	def _connect():
		state["connects"] += 1
		return _DeadlockingConn(db.connect())

	monkeypatch.setattr(target_module, "_connect", _connect)
	return state


# ============================================================================
# D: 共通アドバイザリーロックと実行順
# ============================================================================

@pytest.mark.parametrize("role_id", [MEMBER, SUB, OBOG, PRE])
def test_patch_manifest_acquires_membership_lock_first_when_membership_role_changed(db, role_id):
	db.add_role("r-meta")
	audit = TEST_AUDIT.with_operation("manifest_patch")

	manifest_repository.patch_manifest_db(
		[], [], [_role("r-meta", name="renamed")], [],
		{role_id: [USER]},
		audit,
	)

	# 監査スナップショット（FOR UPDATE）や割当変更より先に共通ロックを取る
	assert db.executed[0] == LOCK_SQL
	assert db.advisory_locks[0] == "membership"
	assert set(db.advisory_locks) == {"membership"}


def test_patch_manifest_acquires_membership_lock_first_when_clearing_membership_role(db):
	db.assign(MEMBER, USER)
	db.add_membership(USER, "member")
	audit = TEST_AUDIT.with_operation("manifest_patch")

	# upsert_role_assignments では空リスト（全員を外す操作）でも会員種別ロールが含まれるため先頭でロックを取る
	manifest_repository.patch_manifest_db([], [], [], [], {MEMBER: []}, audit)

	assert db.executed[0] == LOCK_SQL
	assert db.advisory_locks[0] == "membership"
	assert set(db.advisory_locks) == {"membership"}


@pytest.mark.parametrize("role_id", [MEMBER, SUB, OBOG, PRE])
def test_replace_manifest_acquires_membership_lock_first_when_membership_role_present(db, role_id):
	db.assign(role_id, USER)
	db.add_membership(USER, {MEMBER: "member", SUB: "sub_user", OBOG: "obog", PRE: "pre_member"}[role_id])
	audit = TEST_AUDIT.with_operation("manifest_put")

	# PUT では空リスト（全員を外す操作）でも会員種別ロールが含まれるため先頭でロックを取る
	manifest_repository.replace_manifest([], [], {role_id: []}, audit)

	assert db.executed[0] == LOCK_SQL
	assert db.advisory_locks[0] == "membership"
	assert set(db.advisory_locks) == {"membership"}


@pytest.mark.parametrize(
	"assignments",
	[
		pytest.param({}, id="no-assignments"),
		pytest.param({GENERAL: [USER]}, id="general-role"),
		pytest.param({ADMIN: [USER]}, id="admin-role"),
	],
)
def test_patch_manifest_does_not_lock_without_membership_role_changes(db, assignments):
	manifest_repository.patch_manifest_db([], [], [], [], assignments, TEST_AUDIT.with_operation("manifest_patch"))

	assert db.advisory_locks == []


@pytest.mark.parametrize(
	"assignments",
	[
		pytest.param({}, id="no-assignments"),
		pytest.param({GENERAL: [USER]}, id="general-role"),
		pytest.param({ADMIN: [USER]}, id="admin-role"),
	],
)
def test_replace_manifest_does_not_lock_without_membership_roles(db, assignments):
	manifest_repository.replace_manifest([], [], assignments, TEST_AUDIT.with_operation("manifest_put"))

	assert db.advisory_locks == []


def test_apply_membership_changes_still_acquires_shared_lock_as_safety_net(db):
	db.assign(MEMBER, USER)
	with db.connect() as conn:
		with conn.cursor() as cur:
			membership_assignment_repository.apply_membership_changes(cur, {MEMBER: ([USER], [])})

	assert db.advisory_locks == ["membership"]


def test_add_to_member_list_acquires_membership_lock_before_checks(db):
	db.add_membership(USER, "pre_member")
	db.assign(PRE, USER)

	membership_repository.add_to_member_list(USER, "111", None, TEST_AUDIT.with_operation("member_add"))

	assert db.executed[0] == LOCK_SQL
	assert db.advisory_locks == ["membership"]
	# ロックの後に member / sub_user の確認を行う
	assert "membership_type = 'member'" in db.executed[1]


def test_add_to_member_list_locks_before_rejecting_sub_user(db):
	db.add_membership(USER, "sub_user")

	with pytest.raises(ValueError):
		membership_repository.add_to_member_list(USER, "111", None, TEST_AUDIT.with_operation("member_add"))

	assert db.executed[0] == LOCK_SQL
	assert db.advisory_locks == ["membership"]


def test_promotion_acquires_membership_lock_before_pre_member_for_update(db):
	db.add_membership(USER, "pre_member", assigned_by="S")
	db.paid_invitations.add(USER)
	db.assign(PRE, USER)

	result = _promote(audit=TEST_AUDIT.with_operation("student_profile"))

	assert result == ("prof_1", True)
	assert db.executed[0] == LOCK_SQL
	assert db.advisory_locks == ["membership"]
	assert "membership_type = 'pre_member'" in db.executed[1] and "FOR UPDATE" in db.executed[1]


def test_profile_update_without_eligibility_does_not_acquire_membership_lock(db):
	db.add_membership(USER, "sub_user")

	result = _promote(require_eligibility=False, audit=TEST_AUDIT.with_operation("student_profile"))

	assert result == ("prof_1", False)
	assert db.advisory_locks == []


# ============================================================================
# B: DeadlockDetected の 1 回リトライと WARNING ログ
# ============================================================================

def test_retry_on_deadlock_retries_once_and_logs_function_name_only(caplog):
	attempts = 0
	secret_arg = "applicant@example.com"

	@connection.retry_on_deadlock
	def sample_repo_op(email: str) -> str:
		nonlocal attempts
		attempts += 1
		if attempts == 1:
			raise pg_errors.DeadlockDetected(f"detail with {email}")
		return "ok"

	with caplog.at_level(logging.WARNING, logger=connection.logger.name):
		assert sample_repo_op(secret_arg) == "ok"

	assert attempts == 2
	assert len(caplog.records) == 1
	assert caplog.records[0].levelno == logging.WARNING
	assert "sample_repo_op" in caplog.records[0].getMessage()
	assert secret_arg not in caplog.records[0].getMessage()


def test_retry_on_deadlock_raises_when_second_attempt_also_deadlocks(caplog):
	attempts = 0

	@connection.retry_on_deadlock
	def always_deadlock() -> None:
		nonlocal attempts
		attempts += 1
		raise pg_errors.DeadlockDetected("deadlock")

	with caplog.at_level(logging.WARNING, logger=connection.logger.name):
		with pytest.raises(pg_errors.DeadlockDetected):
			always_deadlock()

	assert attempts == 2
	assert len(caplog.records) == 1


def test_retry_on_deadlock_does_not_retry_other_exceptions(caplog):
	attempts = 0

	@connection.retry_on_deadlock
	def other_error() -> None:
		nonlocal attempts
		attempts += 1
		raise ValueError("not a deadlock")

	with caplog.at_level(logging.WARNING, logger=connection.logger.name):
		with pytest.raises(ValueError):
			other_error()

	assert attempts == 1
	assert caplog.records == []


def test_patch_manifest_retries_once_on_deadlock_and_applies_once(db, monkeypatch, caplog):
	audit = TEST_AUDIT.with_operation("manifest_patch")
	state = _inject_deadlock_on_sql(monkeypatch, db, manifest_repository, "INSERT INTO user_memberships", fail_times=1)

	with caplog.at_level(logging.WARNING, logger=connection.logger.name):
		manifest_repository.patch_manifest_db([], [], [], [], {MEMBER: [USER]}, audit)

	assert state["connects"] == 2
	assert db.rollbacks == 1
	assert db.members_of(MEMBER) == {USER}
	assert db.membership_types_of(USER) == {"member"}
	# 1 回目の変更はロールバックされ、監査ログも 1 回分だけ残る
	assert [log["target_type"] for log in db.audit_logs] == ["membership", "role_assignment"]
	assert any("patch_manifest_db" in rec.getMessage() for rec in caplog.records)


def test_patch_manifest_raises_on_second_deadlock_without_partial_writes(db, monkeypatch):
	_inject_deadlock_on_sql(monkeypatch, db, manifest_repository, "INSERT INTO user_memberships", fail_times=2)

	with pytest.raises(pg_errors.DeadlockDetected):
		manifest_repository.patch_manifest_db(
			[], [], [], [], {MEMBER: [USER]}, TEST_AUDIT.with_operation("manifest_patch"),
		)

	assert db.rollbacks == 2
	assert db.assignments == set()
	assert db.memberships == {}
	assert db.audit_logs == []


def test_replace_manifest_retries_once_on_deadlock_and_applies_once(db, monkeypatch, caplog):
	audit = TEST_AUDIT.with_operation("manifest_put")
	state = _inject_deadlock_on_sql(monkeypatch, db, manifest_repository, "INSERT INTO user_memberships", fail_times=1)

	with caplog.at_level(logging.WARNING, logger=connection.logger.name):
		manifest_repository.replace_manifest([], [_role(MEMBER)], {MEMBER: [USER]}, audit)

	assert state["connects"] == 2
	assert db.rollbacks == 1
	assert db.members_of(MEMBER) == {USER}
	assert db.membership_types_of(USER) == {"member"}
	assert [log["target_type"] for log in db.audit_logs] == ["membership", "role", "role_assignment"]
	assert any("replace_manifest" in rec.getMessage() for rec in caplog.records)


def test_replace_manifest_raises_on_second_deadlock(db, monkeypatch):
	_inject_deadlock_on_sql(monkeypatch, db, manifest_repository, "INSERT INTO user_memberships", fail_times=2)

	with pytest.raises(pg_errors.DeadlockDetected):
		manifest_repository.replace_manifest([], [_role(MEMBER)], {MEMBER: [USER]})

	assert db.rollbacks == 2
	assert db.roles == {}
	assert db.assignments == set()
	assert db.memberships == {}


def test_add_to_member_list_retries_once_on_deadlock_and_applies_once(db, monkeypatch, caplog):
	db.add_membership(USER, "pre_member")
	db.assign(PRE, USER)
	state = _inject_deadlock_on_sql(
		monkeypatch, db, membership_repository, "INSERT INTO role_member_assignments", fail_times=1,
	)

	with caplog.at_level(logging.WARNING, logger=connection.logger.name):
		result = membership_repository.add_to_member_list(USER, "111", None, TEST_AUDIT.with_operation("member_add"))

	assert result["added_to_member_list"] is True
	assert state["connects"] == 2
	assert db.rollbacks == 1
	assert db.membership_types_of(USER) == {"member"}
	assert db.assignments == {(MEMBER, USER)}
	assert len(db.audit_logs) == 1
	assert any("add_to_member_list" in rec.getMessage() for rec in caplog.records)


@pytest.mark.asyncio
async def test_add_member_endpoint_returns_500_when_deadlock_persists(db, monkeypatch):
	db.add_membership(USER, "pre_member")
	_inject_deadlock_on_sql(
		monkeypatch, db, membership_repository, "INSERT INTO role_member_assignments", fail_times=2,
	)

	with pytest.raises(HTTPException) as exc_info:
		await members_api.add_member(
			members_api.AddMemberRequest(discord_id=USER),
			_principal={"sub": "sub-1", "discord_id": "111"},
			audit=TEST_AUDIT,
		)

	assert exc_info.value.status_code == 500
	assert exc_info.value.detail == "Failed to add member"
	assert db.membership_types_of(USER) == {"pre_member"}
	assert db.assignments == set()


def test_promotion_retries_once_on_deadlock_and_applies_once(db, monkeypatch, caplog):
	db.add_membership(USER, "pre_member", assigned_by="S")
	db.paid_invitations.add(USER)
	db.assign(PRE, USER)
	state = _inject_deadlock_on_sql(
		monkeypatch, db, student_repository, "INSERT INTO role_member_assignments", fail_times=1,
	)

	with caplog.at_level(logging.WARNING, logger=connection.logger.name):
		result = _promote(audit=TEST_AUDIT.with_operation("student_profile"))

	assert result == ("prof_1", True)
	assert state["connects"] == 2
	assert db.rollbacks == 1
	assert db.membership_types_of(USER) == {"member"}
	assert db.assignments == {(MEMBER, USER)}
	assert USER in db.student_profiles
	assert len(db.audit_logs) == 1
	assert any("upsert_student_profile_and_promote" in rec.getMessage() for rec in caplog.records)


def test_promotion_raises_on_second_deadlock_without_partial_writes(db, monkeypatch):
	db.add_membership(USER, "pre_member", assigned_by="S")
	db.paid_invitations.add(USER)
	db.assign(PRE, USER)
	_inject_deadlock_on_sql(
		monkeypatch, db, student_repository, "INSERT INTO role_member_assignments", fail_times=2,
	)

	with pytest.raises(pg_errors.DeadlockDetected):
		_promote(audit=TEST_AUDIT.with_operation("student_profile"))

	assert db.rollbacks == 2
	assert db.membership_types_of(USER) == {"pre_member"}
	assert db.assignments == {(PRE, USER)}
	assert db.student_profiles == {}
	assert db.audit_logs == []


# ============================================================================
# 本会員化の入会資格チェック（member / sub_user の行および sub垢 割当を 403 で拒否）
# ============================================================================

@pytest.mark.parametrize("conflict", ["sub_user_row", "member_row", "sub_user_assignment"])
def test_promotion_rejects_existing_member_or_sub_user_and_rolls_back(db, conflict):
	db.add_membership(USER, "pre_member", assigned_by="S")
	db.paid_invitations.add(USER)
	db.assign(PRE, USER)
	if conflict == "sub_user_row":
		db.add_membership(USER, "sub_user")
	elif conflict == "member_row":
		db.add_membership(USER, "member")
	else:
		db.assign(SUB, USER)
	before = (dict(db.memberships), set(db.assignments), dict(db.student_profiles), list(db.audit_logs))

	with pytest.raises(RegistrationNotEligibleError, match="新規入会の対象外です"):
		_promote(audit=TEST_AUDIT.with_operation("student_profile"))

	assert db.rollbacks == 1
	assert (db.memberships, db.assignments, db.student_profiles, db.audit_logs) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("conflict", ["sub_user_row", "member_row", "sub_user_assignment"])
async def test_create_student_profile_returns_403_for_sub_user_or_member_entering_new_registration(
	db, monkeypatch, conflict,
):
	"""JWT の app_role が pre_member のまま等で新規入会経路に入った場合も、403 を返し何も変更しない（#264）。"""
	db.add_membership(USER, "pre_member", assigned_by="S")
	db.paid_invitations.add(USER)
	db.assign(PRE, USER)
	if conflict == "sub_user_row":
		db.add_membership(USER, "sub_user")
	elif conflict == "member_row":
		db.add_membership(USER, "member")
	else:
		db.assign(SUB, USER)

	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: True)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: True)
	monkeypatch.setattr(student_api.student_repository, "get_latest_verified_otp", lambda discord_id: {"verified": True})
	monkeypatch.setenv("DISCORD_TOKEN", "dummy-token")
	monkeypatch.setenv("DISCORD_GUILD_ID", "dummy-guild")
	discord_calls: list = []
	monkeypatch.setattr(student_api, "add_role_to_member", lambda *args, **kwargs: discord_calls.append(args))
	before = (dict(db.memberships), set(db.assignments), dict(db.student_profiles), list(db.audit_logs))

	req = student_api.StudentProfileRequest(
		student_number="1A234567",
		name="テスト 太郎",
		furigana="テスト タロウ",
		department="テスト学部",
		gender=None,
		phone="09000000000",
	)
	with pytest.raises(HTTPException) as exc_info:
		await student_api.create_student_profile(
			req,
			principal={"sub": "sub-1", "discord_id": USER, "app_role": "pre_member"},
			audit=TEST_AUDIT,
		)

	assert exc_info.value.status_code == 403
	assert exc_info.value.detail == "新規入会の対象外です"
	assert (db.memberships, db.assignments, db.student_profiles, db.audit_logs) == before
	assert discord_calls == []
