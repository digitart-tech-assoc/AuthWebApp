"""会員種別を変える経路の共通ロック・デッドロック時のリトライ・本会員化の入会資格のテスト（#264）

- 保存（PUT / PATCH）・/members/member/add・本会員化は、トランザクションの最初の文として共通のロックを取る
- デッドロック（DeadlockDetected）で失敗したら、関数全体を 1 回だけ呼び直す
- 本会員化で、member / sub_user の行または sub垢 の割当がある人は 403 にし、何も変えない

実 DB での並行実行のテストは、今のテスト基盤にないため対象外とする。
"""

import logging

import pytest
from fastapi import HTTPException
from psycopg2 import errors as pg_errors

from app.api.v1 import members as members_api
from app.api.v1 import student as student_api
from app.core.exceptions import RegistrationNotEligibleError
from app.db import (
	guild_repository,
	manifest_repository,
	membership_assignment_repository,
	membership_repository,
	student_repository,
)
from app.db.audit_repository import AuditContext
from app.db.connection import retry_on_deadlock
from tests.fake_role_db import FakeRoleDB

MEMBER, SUB, OBOG, PRE, ADMIN = "role-member", "role-sub", "role-obog", "role-pre", "role-admin"
GAME = "role-game"
USER = "100"
LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtext(%s))"
AUDIT = AuditContext(request_id="req-1", actor_sub="sub-1", actor_discord_id="111", operation="test")


@pytest.fixture(autouse=True)
def role_env(monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", MEMBER)
	monkeypatch.setenv("SUB_USER_ROLE_IDS", SUB)
	monkeypatch.setenv("OBOG_ROLE_IDS", OBOG)
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", PRE)
	monkeypatch.setenv("ADMIN_ROLE_IDS", ADMIN)


@pytest.fixture
def db(monkeypatch):
	fake = FakeRoleDB()
	for module in (manifest_repository, guild_repository, membership_repository, student_repository):
		monkeypatch.setattr(module, "_connect", fake.connect)
	return fake


def _patch(changes, audit=AUDIT):
	manifest_repository.patch_manifest_db([], [], [], [], changes, audit)


def _add(*user_ids):
	return {"added": list(user_ids), "removed": []}


def _put(assignments, audit=AUDIT):
	manifest_repository.replace_manifest([], [], assignments, audit)


def _patch_to(db, assignments):
	# PATCH は割当の差分を送るため、変更後の全員の一覧を、今の割当との差分にして送る
	_patch({
		role_id: {
			"added": sorted(set(users) - db.members_of(role_id)),
			"removed": sorted(db.members_of(role_id) - set(users)),
		}
		for role_id, users in assignments.items()
	})


def _put_to(db, assignments):
	_put(assignments)


def _promote(require_eligibility=True, audit=AUDIT):
	return student_repository.upsert_student_profile_and_promote(
		profile_id="prof_test",
		discord_id=USER,
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
		sub_user_role_ids=[SUB],
	)


def _eligible(db):
	db.add_membership(USER, "pre_member", "S")
	db.assign(PRE, USER)
	db.paid_invitations.add(USER)


def _state(db):
	return (
		set(db.assignments), dict(db.memberships), set(db.paid_invitations),
		dict(db.student_profiles), list(db.audit_logs),
	)


# --- ロックを取る順序 ---

@pytest.mark.parametrize("audit", [AUDIT, None], ids=["with-audit", "without-audit"])
def test_patch_takes_lock_first(db, audit):
	# 監査ありでは、マニフェストの行の FOR UPDATE より前に取る
	_patch({MEMBER: _add(USER)}, audit)

	assert db.executed[0] == LOCK_SQL
	assert set(db.advisory_locks) == {"membership"}
	assert db.membership_types_of(USER) == {"member"}


@pytest.mark.parametrize("audit", [AUDIT, None], ids=["with-audit", "without-audit"])
def test_put_takes_lock_first(db, audit):
	_put({MEMBER: [USER], GAME: []}, audit)

	assert db.executed[0] == LOCK_SQL
	assert db.membership_types_of(USER) == {"member"}


SAVES = [pytest.param(_patch_to, id="patch"), pytest.param(_put_to, id="put")]
ROW_TYPES = {MEMBER: "member", SUB: "sub_user", OBOG: "obog", PRE: "pre_member"}


@pytest.mark.parametrize("save", SAVES)
@pytest.mark.parametrize("role_id", [MEMBER, SUB, OBOG, PRE])
def test_save_takes_lock_first_for_each_membership_role(db, save, role_id):
	save(db, {role_id: [USER]})

	assert db.executed[0] == LOCK_SQL
	assert set(db.advisory_locks) == {"membership"}
	assert db.membership_types_of(USER) == {ROW_TYPES[role_id]}


@pytest.mark.parametrize("save", SAVES)
@pytest.mark.parametrize("role_id", [MEMBER, SUB, OBOG, PRE])
def test_save_clearing_membership_role_takes_lock_first(db, save, role_id):
	# 空のリスト（全員を外す保存）でも、会員種別のロールを送るため最初に取る
	db.assign(role_id, USER)
	db.add_membership(USER, ROW_TYPES[role_id])

	save(db, {role_id: []})

	assert db.executed[0] == LOCK_SQL
	assert set(db.advisory_locks) == {"membership"}
	assert db.membership_types_of(USER) == set()


@pytest.mark.parametrize("save", SAVES)
@pytest.mark.parametrize("assignments", [
	pytest.param({}, id="no-assignments"),
	pytest.param({GAME: [USER, "200"]}, id="general-role"),
	pytest.param({ADMIN: [USER]}, id="admin-role"),
])
def test_save_without_membership_roles_takes_no_lock(db, save, assignments):
	# admin のロールは保存で種別を更新しないため、会員種別のロールに含めない
	save(db, assignments)

	assert db.advisory_locks == []
	for role_id, users in assignments.items():
		assert db.members_of(role_id) == set(users)


def test_apply_membership_changes_takes_lock_as_safety_net(db):
	# 呼び出し元が取り忘れても、種別を変えるときは apply_membership_changes の中で取る
	db.assign(MEMBER, USER)
	with db.connect() as conn:
		with conn.cursor() as cur:
			membership_assignment_repository.apply_membership_changes(cur, {MEMBER: ([USER], [])})

	assert db.advisory_locks == ["membership"]
	assert db.membership_types_of(USER) == {"member"}


def test_save_with_unconfigured_membership_env_takes_no_lock(db, monkeypatch):
	for name in ("MEMBER_ROLE_IDS", "SUB_USER_ROLE_IDS", "OBOG_ROLE_IDS", "PRE_MEMBER_ROLE_ID"):
		monkeypatch.delenv(name)

	_patch({MEMBER: _add(USER)})

	assert db.advisory_locks == []


@pytest.mark.parametrize("held", [None, "member"], ids=["pre-member", "already-member"])
def test_member_add_takes_lock_before_checks(db, held):
	# member / sub垢 の確認より前に取る（確認だけで終わる場合も同じ）
	_eligible(db)
	if held:
		db.add_membership(USER, held)

	membership_repository.add_to_member_list(USER, "111", None, AUDIT)

	assert db.executed[0] == LOCK_SQL
	assert db.advisory_locks == ["membership"]


def test_promotion_takes_lock_before_row_locks(db):
	_eligible(db)

	assert _promote() == ("prof_test", True)

	assert db.executed[0] == LOCK_SQL
	assert "FOR UPDATE" in db.executed[1]
	assert db.membership_types_of(USER) == {"member"}


def test_profile_update_takes_no_lock(db):
	db.add_membership(USER, "sub_user")

	assert _promote(require_eligibility=False) == ("prof_test", False)

	assert db.advisory_locks == []


# --- デッドロック時のリトライ（デコレーター単体） ---

def test_retry_on_deadlock_retries_once_and_logs_function_name_only(caplog):
	# 引数にも例外の文にも個人情報（ダミー）を入れ、どちらもログに出ないことを確かめる
	secret = "applicant@example.com"
	calls = []

	@retry_on_deadlock
	def save(email):
		calls.append(email)
		if len(calls) == 1:
			raise pg_errors.DeadlockDetected(f"deadlock detected: {email}")
		return "ok"

	with caplog.at_level(logging.WARNING, logger="app.db.connection"):
		assert save(secret) == "ok"

	assert calls == [secret, secret]
	assert [r.levelno for r in caplog.records] == [logging.WARNING]
	assert caplog.records[0].getMessage() == "Deadlock detected; retrying once: save"
	assert secret not in caplog.text


def test_retry_on_deadlock_raises_when_second_attempt_fails():
	calls = []

	@retry_on_deadlock
	def save():
		calls.append(1)
		raise pg_errors.DeadlockDetected("deadlock detected")

	with pytest.raises(pg_errors.DeadlockDetected):
		save()

	assert len(calls) == 2


@pytest.mark.parametrize("error", [
	pg_errors.LockNotAvailable("lock timeout"),
	pg_errors.SerializationFailure("serialization failure"),
	ValueError("invalid"),
])
def test_retry_on_deadlock_does_not_retry_other_errors(error):
	calls = []

	@retry_on_deadlock
	def save():
		calls.append(1)
		raise error

	with pytest.raises(type(error)):
		save()

	assert len(calls) == 1


# --- デッドロック時のリトライ（対象の経路） ---

# (pre_member かつ支払済みの状態を用意するか, 実行する経路, 1 回だけ実行したときの監査ログの (target_type, target_id))
SAVE_AUDIT = [("membership", USER), ("role_assignment", MEMBER)]
MEMBER_ROLES_AUDIT = [("member_roles", USER)]
RETRY_CASES = [
	pytest.param(False, lambda: _patch({MEMBER: _add(USER)}), SAVE_AUDIT, id="patch"),
	pytest.param(False, lambda: _put({MEMBER: [USER]}), SAVE_AUDIT, id="put"),
	pytest.param(
		True, lambda: membership_repository.add_to_member_list(USER, "111", None, AUDIT), MEMBER_ROLES_AUDIT,
		id="member-add",
	),
	pytest.param(True, _promote, MEMBER_ROLES_AUDIT, id="promotion"),
]


@pytest.mark.parametrize(("eligible", "run", "expected_audit"), RETRY_CASES)
def test_deadlock_is_retried_once_and_applied_once(db, eligible, run, expected_audit, caplog):
	# user_memberships の INSERT でデッドロックし、1 回目のトランザクションはロールバックされる
	if eligible:
		_eligible(db)
	db.deadlock_on = "INSERT INTO user_memberships"
	db.deadlocks = 1

	with caplog.at_level(logging.WARNING, logger="app.db.connection"):
		run()

	assert db.deadlocks == 0
	assert db.rollbacks == 1
	assert db.membership_types_of(USER) == {"member"}
	assert db.members_of(MEMBER) == {USER}
	assert db.members_of(PRE) == set()
	# 監査ログもロールバックされ、2 回目の分だけが残る
	assert [(log["target_type"], log["target_id"]) for log in db.audit_logs] == expected_audit
	assert "retrying once" in caplog.text
	assert USER not in caplog.text


@pytest.mark.parametrize(("eligible", "run", "expected_audit"), RETRY_CASES)
def test_deadlock_twice_raises_and_changes_nothing(db, eligible, run, expected_audit):
	# 2 回目も失敗したら例外をそのまま送出する（ルーターでは今と同じく 500 になる）
	if eligible:
		_eligible(db)
	db.deadlock_on = "INSERT INTO user_memberships"
	db.deadlocks = 2
	before = _state(db)

	with pytest.raises(pg_errors.DeadlockDetected):
		run()

	assert db.rollbacks == 2
	assert _state(db) == before


@pytest.mark.asyncio
async def test_member_add_endpoint_returns_500_when_deadlock_persists(db):
	# 2 回目も失敗したら、今と同じく 500（固定文言）になり、何も変わらない
	_eligible(db)
	db.deadlock_on = "INSERT INTO user_memberships"
	db.deadlocks = 2
	before = _state(db)

	with pytest.raises(HTTPException) as error:
		await members_api.add_member(
			members_api.AddMemberRequest(discord_id=USER),
			_principal={"sub": "sub-1", "discord_id": "111"},
			audit=AUDIT,
		)

	assert error.value.status_code == 500
	assert error.value.detail == "Failed to add member"
	assert db.rollbacks == 2
	assert _state(db) == before


# --- 本会員化の入会資格（member / sub垢 の人は 403） ---

@pytest.mark.parametrize("setup", ["sub_user-row", "sub-assignment", "member-row"])
def test_promotion_rejects_member_or_sub_user(db, setup):
	_eligible(db)
	if setup == "sub_user-row":
		db.add_membership(USER, "sub_user")
	elif setup == "sub-assignment":
		db.assign(SUB, USER)
	else:
		db.add_membership(USER, "member")
	before = _state(db)

	with pytest.raises(RegistrationNotEligibleError) as error:
		_promote()

	assert str(error.value) == student_repository.NOT_ELIGIBLE_ALREADY_MEMBER
	assert _state(db) == before
	assert db.rollbacks == 1
	assert db.writes() == []


def test_promotion_allows_obog_row(db):
	# obog は member / sub垢 と同時に持てない種別ではないため、入会資格の判定には含めない
	_eligible(db)
	db.add_membership(USER, "obog")

	assert _promote() == ("prof_test", True)

	assert db.membership_types_of(USER) == {"member", "obog"}


@pytest.mark.asyncio
async def test_create_profile_returns_403_for_sub_user_in_registration_path(db, monkeypatch):
	# 認証時の app_role が pre_member でも（JWT の claim が古い場合など）、
	# sub_user の行がある人は本会員化せず、プロフィールも保存しない
	_eligible(db)
	db.add_membership(USER, "sub_user")
	before = _state(db)
	monkeypatch.setenv("DISCORD_TOKEN", "dummy-token")
	monkeypatch.setenv("DISCORD_GUILD_ID", "dummy-guild")
	monkeypatch.setattr(student_api, "_is_pre_member", lambda discord_id: True)
	monkeypatch.setattr(student_api, "_is_paid_invitation", lambda discord_id: True)
	monkeypatch.setattr(
		student_api.student_repository, "get_latest_verified_otp", lambda discord_id: {"verified": True},
	)

	async def _forbid_discord(*args, **kwargs):
		pytest.fail("add_role_to_member must not be called")

	monkeypatch.setattr(student_api, "add_role_to_member", _forbid_discord)

	with pytest.raises(HTTPException) as error:
		await student_api.create_student_profile(
			student_api.StudentProfileRequest(
				student_number="1A234567", name="テスト 太郎", furigana="テスト タロウ",
				department="テスト学部", gender=None, phone="09000000000",
			),
			principal={"discord_id": USER, "app_role": "pre_member"},
			audit=AUDIT,
		)

	assert error.value.status_code == 403
	assert error.value.detail == student_repository.NOT_ELIGIBLE_ALREADY_MEMBER
	assert _state(db) == before
