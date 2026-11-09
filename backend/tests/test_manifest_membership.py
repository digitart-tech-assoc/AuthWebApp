"""管理画面の割当の保存で、会員種別（user_memberships）を更新することのテスト（#251）

- 会員種別のロールの割当が変わった人の、変わった種別の行だけを同じトランザクションで更新する
- admin の行は保存では変更しない
- 1 種別に複数ロールがある場合の一部だけの付け外し、member と sub垢 の両方などは拒否してロールバックする
"""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.v1 import manifest as manifest_api
from app.core.auth import get_current_principal
from app.db import guild_repository, manifest_repository
from app.db.audit_repository import AuditContext, get_audit_context
from app.core.exceptions import MembershipAssignmentError
from tests.fake_role_db import FakeRoleDB

AUDIT = AuditContext(request_id="req-1", actor_sub="sub-1", actor_discord_id="111", operation="manifest_patch")
MEMBER, SUB, OBOG, PRE, ADMIN = "role-member", "role-sub", "role-obog", "role-pre", "role-admin"
USER = "100"


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
	monkeypatch.setattr(manifest_repository, "_connect", fake.connect)
	monkeypatch.setattr(guild_repository, "_connect", fake.connect)
	return fake


def _patch(assignments, audit=AUDIT):
	manifest_repository.patch_manifest_db([], [], [], [], assignments, audit)


def _membership_logs(db):
	return [log for log in db.audit_logs if log["target_type"] == "membership"]


# --- 失効・付与 ---

@pytest.mark.parametrize(("role_id", "m_type"), [(MEMBER, "member"), (PRE, "pre_member"), (SUB, "sub_user"), (OBOG, "obog")])
def test_removing_role_removes_membership(db, role_id, m_type):
	db.assign(role_id, USER, "200")
	db.add_membership(USER, m_type)
	db.add_membership("200", m_type)

	_patch({role_id: ["200"]})

	assert db.membership_types_of(USER) == set()
	assert db.membership_types_of("200") == {m_type}
	assert _membership_logs(db) == [{
		"request_id": "req-1", "operation": "manifest_patch", "system": "db",
		"target_type": "membership", "target_id": USER, "action": "update",
		"before": None, "after": {"added": [], "removed": [m_type]},
		"actor_sub": "sub-1", "actor_discord_id": "111",
	}]


def test_adding_role_adds_membership_with_assigned_by(db):
	_patch({MEMBER: [USER]})

	assert db.memberships == {(USER, "member"): "111"}
	assert _membership_logs(db)[0]["after"] == {"added": ["member"], "removed": []}


def test_member_to_obog_does_not_leave_member(db):
	db.assign(MEMBER, USER)
	db.add_membership(USER, "member")

	_patch({MEMBER: [], OBOG: [USER]})

	assert db.membership_types_of(USER) == {"obog"}
	assert _membership_logs(db)[0]["after"] == {"added": ["obog"], "removed": ["member"]}


def test_pre_member_to_member(db):
	db.assign(PRE, USER)
	db.add_membership(USER, "pre_member")

	_patch({PRE: [], MEMBER: [USER]})

	assert db.membership_types_of(USER) == {"member"}


def test_unchanged_user_rows_are_kept(db):
	# 割当がなく行だけある人は、保存で割当を変えていないので失効させない
	db.assign(MEMBER, "200")
	db.add_membership(USER, "member")

	_patch({MEMBER: ["200", "300"]})

	assert db.membership_types_of(USER) == {"member"}
	assert db.membership_types_of("300") == {"member"}


def test_existing_row_is_not_overwritten(db):
	db.assign(MEMBER, USER)
	db.add_membership(USER, "member", assigned_by="original")
	db.add_membership("200", "member", assigned_by="original")

	_patch({MEMBER: [USER, "200"]})

	assert db.memberships[("200", "member")] == "original"
	assert _membership_logs(db) == []


def test_admin_rows_are_not_changed_by_save(db):
	db.assign(ADMIN, USER)
	db.add_membership(USER, "admin")

	_patch({ADMIN: [], MEMBER: ["200"]})

	assert db.membership_types_of(USER) == {"admin"}
	assert db.membership_types_of("200") == {"member"}


def test_non_membership_roles_do_not_touch_memberships(db):
	db.add_membership(USER, "member")

	_patch({"role-game": [USER, "200"]})

	assert db.memberships == {(USER, "member"): None}
	assert not any("user_memberships" in sql for sql in db.executed)


def test_put_updates_memberships(db):
	db.assign(MEMBER, USER)
	db.add_membership(USER, "member")

	manifest_repository.replace_manifest([], [], {MEMBER: []}, AUDIT)

	assert db.membership_types_of(USER) == set()


def test_unconfigured_env_skips_membership_update(db, monkeypatch):
	monkeypatch.delenv("MEMBER_ROLE_IDS")
	db.assign(MEMBER, USER)
	db.add_membership(USER, "member")

	_patch({MEMBER: []})

	assert db.membership_types_of(USER) == {"member"}


# --- 1 種別に複数ロール ---

def test_partial_removal_of_multiple_member_roles_is_rejected(db, monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", f"{MEMBER},role-member-2")
	db.assign(MEMBER, USER)
	db.assign("role-member-2", USER)
	db.add_membership(USER, "member")

	with pytest.raises(MembershipAssignmentError):
		_patch({"role-member-2": []})

	assert db.members_of("role-member-2") == {USER}
	assert db.membership_types_of(USER) == {"member"}


def test_partial_addition_of_multiple_member_roles_is_rejected(db, monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", f"{MEMBER},role-member-2")

	with pytest.raises(MembershipAssignmentError):
		_patch({MEMBER: [USER]})

	assert db.members_of(MEMBER) == set()
	assert db.memberships == {}


def test_removing_all_multiple_member_roles_revokes(db, monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", f"{MEMBER},role-member-2")
	db.assign(MEMBER, USER)
	db.assign("role-member-2", USER)
	db.add_membership(USER, "member")

	_patch({MEMBER: [], "role-member-2": []})

	assert db.membership_types_of(USER) == set()


# --- 同時に持てない種別 ---

@pytest.mark.parametrize(
	("held", "added"),
	[(MEMBER, SUB), (SUB, MEMBER), (MEMBER, PRE), (PRE, MEMBER), (PRE, SUB), (SUB, PRE)],
)
def test_exclusive_types_are_rejected(db, held, added):
	db.assign(held, USER)

	with pytest.raises(MembershipAssignmentError):
		_patch({added: [USER]})

	assert db.members_of(added) == set()
	assert db.audit_logs == []


@pytest.mark.parametrize(("row_type", "added"), [("sub_user", MEMBER), ("pre_member", MEMBER), ("member", SUB)])
def test_exclusive_type_held_only_by_row_is_rejected(db, row_type, added):
	# 行だけあり割当がない人にも、同時に持てない種別は付けられない
	db.add_membership(USER, row_type)

	with pytest.raises(MembershipAssignmentError):
		_patch({added: [USER]})

	assert db.members_of(added) == set()


def test_memberships_are_locked_per_user_in_order(db):
	_patch({MEMBER: ["300", "200"], OBOG: ["100"], "role-game": ["400"]})

	assert db.advisory_locks == ["membership:100", "membership:200", "membership:300"]


def test_unrelated_type_change_on_partial_holder_is_allowed(db, monkeypatch):
	# 既存データで member ロールの一部だけを持つ人でも、member 以外の種別の変更はできる
	monkeypatch.setenv("MEMBER_ROLE_IDS", f"{MEMBER},role-member-2")
	db.assign(MEMBER, USER)

	_patch({OBOG: [USER]})

	assert db.membership_types_of(USER) == {"obog"}


def test_removing_sub_role_from_legacy_holder_only_removes_sub_user(db):
	# 既存データで member と sub垢 の両方を持つ人。sub垢 を外しても member には変更しない
	db.assign(MEMBER, USER)
	db.assign(SUB, USER)
	db.add_membership(USER, "sub_user")

	_patch({SUB: []})

	assert db.membership_types_of(USER) == set()
	assert db.members_of(MEMBER) == {USER}


def test_removing_member_role_from_legacy_holder_is_allowed(db):
	db.assign(MEMBER, USER)
	db.assign(SUB, USER)
	db.add_membership(USER, "sub_user")

	_patch({MEMBER: []})

	assert db.membership_types_of(USER) == {"sub_user"}


def test_unrelated_type_change_on_legacy_holder_is_allowed(db):
	db.assign(MEMBER, USER)
	db.assign(SUB, USER)

	_patch({OBOG: [USER]})

	assert db.membership_types_of(USER) == {"obog"}


# --- エンドポイント ---

@pytest.fixture
def client():
	main.app.dependency_overrides[get_current_principal] = lambda: {"sub": "sub-1", "discord_id": "111", "app_role": "admin"}
	main.app.dependency_overrides[get_audit_context] = lambda: AuditContext("fixed-req", "sub-1", "111")
	yield TestClient(main.app)
	main.app.dependency_overrides.clear()


def _raise(*_args):
	raise MembershipAssignmentError(MembershipAssignmentError.EXCLUSIVE, USER, ("member", "sub_user"))


def test_patch_endpoint_returns_400_on_invalid_membership(client, monkeypatch):
	monkeypatch.setattr(manifest_api, "patch_manifest_db", _raise)

	res = client.patch("/api/v1/manifest", json={"upsert_role_assignments": {SUB: [USER]}})

	assert res.status_code == 400
	assert res.json()["detail"] == "100: 会員種別 'member' と 'sub_user' のロールを同時に付けることはできません"


def test_put_endpoint_returns_400_on_invalid_membership(client, monkeypatch):
	monkeypatch.setattr(manifest_api, "replace_manifest", _raise)

	res = client.put("/api/v1/manifest", json={"role_assignments": {SUB: [USER]}})

	assert res.status_code == 400
