"""会員種別とロールの割当の既存データの整理（#251 段階 4）のテスト

- sub垢 と member の両方を持つ人は、member の割当（と、sub_user の行があれば member の行）を外す
- 行はあるが割当がない人は、その種別の割当を補完する
- 割当はあるが行がない人は変更せず、件数だけ数える
- 補完すると同時に持てない組（PR A の保存の規則）になる場合は補完しない
- dry-run では何も書き込まない
"""

import json

import pytest

from app.db.audit_repository import AuditContext
from app.db.membership_backfill import plan_backfill, run_backfill
from app.scripts import fix_membership_assignments
from tests.fake_role_db import FakeRoleDB

MEMBER, SUB, OBOG, PRE, ADMIN = "role-member", "role-sub", "role-obog", "role-pre", "role-admin"
TYPE_ROLE_IDS = {"member": (MEMBER,), "sub_user": (SUB,), "obog": (OBOG,), "pre_member": (PRE,), "admin": (ADMIN,)}
AUDIT = AuditContext("req-1", "maintenance-script", None, "membership_backfill")


@pytest.fixture(autouse=True)
def role_env(monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", MEMBER)
	monkeypatch.setenv("SUB_USER_ROLE_IDS", SUB)
	monkeypatch.setenv("OBOG_ROLE_IDS", OBOG)
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", PRE)
	monkeypatch.setenv("ADMIN_ROLE_IDS", ADMIN)


# --- 計画 ---

def test_sub_user_with_member_assignment_loses_member():
	plan = plan_backfill(
		{("1", "sub_user"), ("1", "member")},
		{(SUB, "1"), (MEMBER, "1")},
		TYPE_ROLE_IDS,
	)

	assert plan.remove_assignments == [(MEMBER, "1")]
	assert plan.remove_memberships == [("1", "member")]
	assert plan.add_assignments == []


def test_sub_role_holder_without_row_loses_member_assignment_only():
	# sub_user の行がなくても、sub垢 の割当があれば member の割当を外す。member の行は残す
	plan = plan_backfill({("1", "member")}, {(SUB, "1"), (MEMBER, "1")}, TYPE_ROLE_IDS)

	assert plan.remove_assignments == [(MEMBER, "1")]
	assert plan.remove_memberships == []
	# 外した member の割当を補完し直さない
	assert plan.add_assignments == []


@pytest.mark.parametrize(("m_type", "role_id"), [("member", MEMBER), ("sub_user", SUB), ("obog", OBOG), ("pre_member", PRE)])
def test_row_without_assignment_is_backfilled(m_type, role_id):
	plan = plan_backfill({("1", m_type)}, set(), TYPE_ROLE_IDS)

	assert plan.add_assignments == [(role_id, "1")]


def test_member_row_of_sub_user_is_not_backfilled():
	plan = plan_backfill({("1", "member"), ("1", "sub_user")}, {(SUB, "1")}, TYPE_ROLE_IDS)

	assert plan.add_assignments == []
	assert plan.remove_memberships == [("1", "member")]


def test_pre_member_row_of_member_is_skipped_and_counted():
	plan = plan_backfill({("1", "member"), ("1", "pre_member")}, {(MEMBER, "1")}, TYPE_ROLE_IDS)

	assert plan.add_assignments == []
	assert plan.skipped_conflicting_rows == {"pre_member": 1}


@pytest.mark.parametrize(
	("memberships", "assignments", "skipped"),
	[
		# OTP 検証済みでプロフィール未送信の人（旧 verify_otp が member を足して pre-member を消した）
		pytest.param({("1", "pre_member")}, {(MEMBER, "1")}, {"pre_member": 1}, id="pre-row-member-assignment"),
		pytest.param({("1", "member")}, {(PRE, "1")}, {"member": 1}, id="member-row-pre-assignment"),
		pytest.param({("1", "member"), ("1", "pre_member")}, {(PRE, "1")}, {"member": 1}, id="both-rows-pre-assignment"),
		pytest.param({("1", "pre_member")}, {(SUB, "1")}, {"pre_member": 1}, id="pre-row-sub-assignment"),
		pytest.param({("1", "sub_user"), ("1", "pre_member")}, set(), {"pre_member": 1, "sub_user": 1}, id="sub-and-pre-rows"),
	],
)
def test_backfill_does_not_create_exclusive_assignments(memberships, assignments, skipped):
	# 補完すると、管理画面の保存では拒否する組（pre-member と member / sub垢）になる場合は補完しない
	plan = plan_backfill(memberships, assignments, TYPE_ROLE_IDS)

	assert plan.add_assignments == []
	assert plan.skipped_conflicting_rows == skipped


def test_member_row_of_sub_role_holder_without_sub_row_is_counted():
	# sub垢 の割当はあるが sub_user の行がない member。member の割当は外し、行は残して件数を出す（先に sync で揃える）
	plan = plan_backfill({("1", "member")}, {(SUB, "1")}, TYPE_ROLE_IDS)

	assert plan.add_assignments == []
	assert plan.member_rows_of_sub_role_holders == 1


def test_multiple_member_roles_are_backfilled():
	plan = plan_backfill({("1", "member")}, {("role-member-2", "1")}, {**TYPE_ROLE_IDS, "member": (MEMBER, "role-member-2")})

	assert plan.add_assignments == [(MEMBER, "1")]


def test_admin_is_not_touched():
	# admin の行・割当は、補完・削除・件数のいずれの対象にもしない
	plan = plan_backfill(
		{("1", "admin"), ("2", "admin"), ("2", "sub_user")},
		{(ADMIN, "3"), (ADMIN, "2"), (SUB, "2")},
		TYPE_ROLE_IDS,
	)

	assert plan.add_assignments == []
	assert plan.remove_assignments == []
	assert plan.remove_memberships == []
	assert plan.assignments_without_row == {}


def test_assignment_without_row_is_only_counted():
	plan = plan_backfill(set(), {(MEMBER, "1"), (MEMBER, "2"), (OBOG, "3")}, TYPE_ROLE_IDS)

	assert plan.add_assignments == []
	assert plan.remove_assignments == []
	assert plan.assignments_without_row == {"member": 2, "obog": 1}


def test_consistent_data_needs_no_change():
	plan = plan_backfill(
		{("1", "member"), ("2", "sub_user"), ("3", "pre_member")},
		{(MEMBER, "1"), (SUB, "2"), (PRE, "3"), ("role-game", "1")},
		TYPE_ROLE_IDS,
	)

	assert plan.summary() == {
		"add_assignments": 0, "remove_assignments": 0, "remove_memberships": 0, "users_changed": 0,
		"skipped_conflicting_rows": {}, "member_rows_of_sub_role_holders": 0, "assignments_without_row": {},
	}


# --- 反映 ---

@pytest.fixture
def db():
	fake = FakeRoleDB()
	fake.add_membership("1", "member")
	fake.add_membership("2", "sub_user")
	fake.add_membership("2", "member")
	fake.assign(SUB, "2")
	fake.assign(MEMBER, "2")
	return fake


def test_dry_run_writes_nothing(db):
	before = (set(db.assignments), dict(db.memberships))

	plan = run_backfill(db.connect(), apply=False, audit=AUDIT)

	assert plan.summary()["add_assignments"] == 1
	assert (db.assignments, db.memberships) == before
	assert db.audit_logs == []
	assert db.writes() == []


def test_apply_writes_changes_and_audit_logs(db):
	run_backfill(db.connect(), apply=True, audit=AUDIT)

	assert db.assignments == {(MEMBER, "1"), (SUB, "2")}
	assert db.memberships == {("1", "member"): None, ("2", "sub_user"): None}
	assert [(log["target_type"], log["target_id"], log["after"]) for log in db.audit_logs] == [
		("member_roles", "1", {"added": [MEMBER], "removed": []}),
		("member_roles", "2", {"added": [], "removed": [MEMBER]}),
		("membership", "2", {"added": [], "removed": ["member"]}),
	]
	assert {log["operation"] for log in db.audit_logs} == {"membership_backfill"}
	assert db.commits == 1


def test_script_defaults_to_dry_run(db, monkeypatch, capsys):
	monkeypatch.setattr(fix_membership_assignments, "_connect", db.connect)

	assert fix_membership_assignments.main([]) == 0

	output = json.loads(capsys.readouterr().out)
	assert output["mode"] == "dry-run"
	assert output["add_assignments"] == 1
	assert db.writes() == []


def test_script_output_contains_no_discord_ids(db, monkeypatch, capsys):
	monkeypatch.setattr(fix_membership_assignments, "_connect", db.connect)

	fix_membership_assignments.main(["--apply"])

	out = capsys.readouterr().out
	assert '"1"' not in out and '"2"' not in out
	assert json.loads(out)["mode"] == "apply"


def test_script_reports_unconfigured_optional_types(db, monkeypatch, capsys):
	monkeypatch.delenv("OBOG_ROLE_IDS")
	monkeypatch.setattr(fix_membership_assignments, "_connect", db.connect)

	fix_membership_assignments.main([])

	assert json.loads(capsys.readouterr().out)["unconfigured_role_id_env_vars"] == ["OBOG_ROLE_IDS"]


def test_script_requires_membership_role_ids(db, monkeypatch):
	monkeypatch.delenv("MEMBER_ROLE_IDS")
	monkeypatch.setattr(fix_membership_assignments, "_connect", db.connect)

	assert fix_membership_assignments.main(["--apply"]) == 1
	assert db.writes() == []
