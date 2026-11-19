"""会員種別を変える経路の共通ロック・デッドロック時のリトライ・本会員化の入会資格のテスト（#264）

- 保存（PUT / PATCH）・/members/member/add・本会員化は、トランザクションの最初の文として共通のロックを取る
- デッドロック（DeadlockDetected）で失敗したら、関数全体を 1 回だけ呼び直す

実 DB での並行実行のテストは、今のテスト基盤にないため対象外とする。
"""

import logging

import pytest
from psycopg2 import errors as pg_errors

from app.db import guild_repository, manifest_repository, membership_repository, student_repository
from app.db.audit_repository import AuditContext
from app.db.connection import retry_on_deadlock
from tests.fake_role_db import FakeRoleDB

MEMBER, SUB, OBOG, PRE = "role-member", "role-sub", "role-obog", "role-pre"
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


@pytest.fixture
def db(monkeypatch):
	fake = FakeRoleDB()
	for module in (manifest_repository, guild_repository, membership_repository, student_repository):
		monkeypatch.setattr(module, "_connect", fake.connect)
	return fake


def _patch(changes, audit=AUDIT):
	manifest_repository.patch_manifest_db([], [], [], [], changes, audit)


def _put(assignments, audit=AUDIT):
	manifest_repository.replace_manifest([], [], assignments, audit)


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
	_patch({MEMBER: [USER]}, audit)

	assert db.executed[0] == LOCK_SQL
	assert set(db.advisory_locks) == {"membership"}
	assert db.membership_types_of(USER) == {"member"}


@pytest.mark.parametrize("audit", [AUDIT, None], ids=["with-audit", "without-audit"])
def test_put_takes_lock_first(db, audit):
	_put({MEMBER: [USER], GAME: []}, audit)

	assert db.executed[0] == LOCK_SQL
	assert db.membership_types_of(USER) == {"member"}


def test_save_without_membership_roles_takes_no_lock(db):
	_patch({GAME: [USER]})
	_put({GAME: [USER, "200"]})

	assert db.advisory_locks == []
	assert db.members_of(GAME) == {USER, "200"}


def test_save_with_unconfigured_membership_env_takes_no_lock(db, monkeypatch):
	for name in ("MEMBER_ROLE_IDS", "SUB_USER_ROLE_IDS", "OBOG_ROLE_IDS", "PRE_MEMBER_ROLE_ID"):
		monkeypatch.delenv(name)

	_patch({MEMBER: [USER]})

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
	calls = []

	@retry_on_deadlock
	def save(discord_id):
		calls.append(discord_id)
		if len(calls) == 1:
			raise pg_errors.DeadlockDetected("deadlock detected")
		return "ok"

	with caplog.at_level(logging.WARNING, logger="app.db.connection"):
		assert save(USER) == "ok"

	assert calls == [USER, USER]
	assert [r.levelno for r in caplog.records] == [logging.WARNING]
	assert caplog.records[0].getMessage() == "Deadlock detected; retrying once: save"
	assert USER not in caplog.text


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

# (pre_member かつ支払済みの状態を用意するか, 実行する経路)
RETRY_CASES = [
	pytest.param(False, lambda: _patch({MEMBER: [USER]}), id="patch"),
	pytest.param(False, lambda: _put({MEMBER: [USER]}), id="put"),
	pytest.param(True, lambda: membership_repository.add_to_member_list(USER, "111", None, AUDIT), id="member-add"),
	pytest.param(True, _promote, id="promotion"),
]


@pytest.mark.parametrize(("eligible", "run"), RETRY_CASES)
def test_deadlock_is_retried_once_and_applied_once(db, eligible, run, caplog):
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
	targets = [(log["target_type"], log["target_id"]) for log in db.audit_logs]
	assert len(targets) == len(set(targets))
	assert targets
	assert "retrying once" in caplog.text
	assert USER not in caplog.text


@pytest.mark.parametrize(("eligible", "run"), RETRY_CASES)
def test_deadlock_twice_raises_and_changes_nothing(db, eligible, run):
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

