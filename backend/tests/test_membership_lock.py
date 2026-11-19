"""会員種別を変える経路の共通ロックのテスト（#264）

- 保存（PUT / PATCH）・/members/member/add・本会員化は、トランザクションの最初の文として共通のロックを取る

実 DB での並行実行のテストは、今のテスト基盤にないため対象外とする。
"""

import pytest

from app.db import guild_repository, manifest_repository, membership_repository, student_repository
from app.db.audit_repository import AuditContext
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

