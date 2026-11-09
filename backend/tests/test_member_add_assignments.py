"""/members/member/add で、ロールの割当を種別に合わせることのテスト（#251 段階 4）

- member の割当の追加と pre-member の割当の削除を、member の行の作成と同じトランザクションで行う
- sub垢 の人は、member と sub垢 の両方を持つことになるため拒否する
"""

import pytest

from app.db import membership_repository
from app.db.audit_repository import AuditContext
from tests.fake_role_db import FakeRoleDB

MEMBER, SUB, PRE = "role-member", "role-sub", "role-pre"
AUDIT = AuditContext("req-1", "sub-1", "111", "member_add")


@pytest.fixture(autouse=True)
def role_env(monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", MEMBER)
	monkeypatch.setenv("SUB_USER_ROLE_IDS", SUB)
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", PRE)


@pytest.fixture
def member_db(monkeypatch):
	fake = FakeRoleDB()
	monkeypatch.setattr(membership_repository, "_connect", fake.connect)
	return fake


def test_member_add_creates_member_assignment_and_removes_pre_member(member_db):
	member_db.add_membership("1", "pre_member")
	member_db.assign(PRE, "1")

	result = membership_repository.add_to_member_list("1", "111", None, AUDIT)

	assert result["added_to_member_list"] is True
	assert member_db.membership_types_of("1") == {"member"}
	assert member_db.assignments == {(MEMBER, "1")}
	assert [(log["target_type"], log["after"], log["operation"]) for log in member_db.audit_logs] == [
		("member_roles", {"added": [MEMBER], "removed": [PRE]}, "member_add"),
	]


def test_member_add_with_multiple_member_roles(member_db, monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", f"{MEMBER},role-member-2")
	member_db.add_membership("1", "pre_member")

	membership_repository.add_to_member_list("1", "111", None, AUDIT)

	assert member_db.assignments == {(MEMBER, "1"), ("role-member-2", "1")}


def test_member_add_with_existing_assignment_records_nothing(member_db):
	member_db.add_membership("1", "pre_member")
	member_db.assign(MEMBER, "1")

	membership_repository.add_to_member_list("1", "111", None, AUDIT)

	assert member_db.membership_types_of("1") == {"member"}
	assert member_db.audit_logs == []


def test_member_add_for_existing_member_changes_nothing(member_db):
	member_db.add_membership("1", "member")

	result = membership_repository.add_to_member_list("1", "111", None, AUDIT)

	assert result["added_to_member_list"] is False
	assert member_db.assignments == set()
	assert member_db.audit_logs == []


@pytest.mark.parametrize("setup", ["row", "assignment"])
def test_member_add_rejects_sub_user(member_db, setup):
	if setup == "row":
		member_db.add_membership("1", "sub_user")
	else:
		member_db.assign(SUB, "1")
	before = (set(member_db.assignments), dict(member_db.memberships))

	with pytest.raises(ValueError):
		membership_repository.add_to_member_list("1", "111", None, AUDIT)

	assert (member_db.assignments, member_db.memberships) == before
	assert member_db.audit_logs == []
