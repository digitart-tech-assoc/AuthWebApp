"""マニフェスト・割り当ての保存を差分更新にしたことのテスト"""

import pytest

from app.core.exceptions import RoleAssignmentChangeConflictError
from app.db import guild_repository, manifest_repository
from app.db.audit_repository import AuditContext
from tests.fake_role_db import FakeRoleDB

AUDIT = AuditContext(request_id="req-1", actor_sub="sub-1", actor_discord_id="111", operation="manifest_patch")


@pytest.fixture
def db(monkeypatch):
	fake = FakeRoleDB()
	monkeypatch.setattr(manifest_repository, "_connect", fake.connect)
	monkeypatch.setattr(guild_repository, "_connect", fake.connect)
	return fake


def _role(role_id, **kwargs):
	row = {
		"role_id": role_id, "name": role_id, "color": "#000000", "hoist": False, "mentionable": False,
		"permissions": 0, "position": 1, "category_id": None, "is_our_bot": False,
	}
	row.update(kwargs)
	return row


def _category(id, **kwargs):
	row = {"id": id, "name": id, "display_order": 0, "is_collapsed": False, "permissions": 0, "is_restricted": False}
	row.update(kwargs)
	return row


def _assignment_writes(db):
	return [sql for sql in db.writes() if "role_member_assignments" in sql]


def _change(added=(), removed=()):
	return {"added": list(added), "removed": list(removed)}


def test_patch_assignments_only_touches_added_and_removed_members(db):
	db.add_role("r1")
	db.assign("r1", "100", "200", "300")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": _change(added=["400"], removed=["100"])})

	assert db.members_of("r1") == {"200", "300", "400"}
	writes = _assignment_writes(db)
	# 送っていないメンバー（200, 300）は DELETE・INSERT しない
	assert len(writes) == 2
	assert writes[0].startswith("DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s")
	assert writes[1].startswith("INSERT INTO role_member_assignments")
	assert not any(sql == "DELETE FROM role_member_assignments WHERE role_id = %s" for sql in writes)
	# 割当の一覧を読んで置き換えない
	assert not any(sql.startswith("SELECT user_id FROM role_member_assignments") for sql in db.executed)


def test_patch_keeps_assignment_added_by_other_operation_after_screen_opened(db):
	"""画面を開いた後に self-batch などで付いた割当が、管理者の保存で外れない（#228）。"""
	db.add_role("r1")
	db.assign("r1", "100")
	# 管理者が画面を開いた時点の割当は 100 だけ。その後、200 が self-batch で自分に付けた
	guild_repository.batch_update_user_roles("200", ["r1"], [])
	assert db.members_of("r1") == {"100", "200"}

	# 管理者は画面上で 300 を追加し、100 を外して保存する（200 は画面に表示されていない）
	manifest_repository.patch_manifest_db([], [], [], [], {"r1": _change(added=["300"], removed=["100"])})

	assert db.members_of("r1") == {"200", "300"}


def test_patch_two_admins_editing_same_role_do_not_overwrite_each_other(db):
	"""同じロールを2人の管理者が同時に編集しても、後の保存が先の保存の追加を外さない（#228）。"""
	db.add_role("r1")
	db.assign("r1", "100")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": _change(added=["200"])})
	manifest_repository.patch_manifest_db([], [], [], [], {"r1": _change(added=["300"])})

	assert db.members_of("r1") == {"100", "200", "300"}


def test_patch_role_with_empty_added_and_removed_changes_nothing(db):
	db.add_role("r1")
	db.assign("r1", "100")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": _change(), "r2": {}})

	assert db.members_of("r1") == {"100"}
	assert _assignment_writes(db) == []


def test_patch_already_assigned_or_unassigned_members_write_nothing(db):
	# 追加済みのメンバーの追加・割り当てのないメンバーの削除は、実際の変更にならない
	db.add_role("r1")
	db.assign("r1", "100")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": _change(added=["100"], removed=["999"])}, AUDIT)

	assert db.members_of("r1") == {"100"}
	assert db.audit_logs == []


def test_patch_duplicated_ids_are_applied_once(db):
	db.add_role("r1")
	db.assign("r1", "100")

	manifest_repository.patch_manifest_db(
		[], [], [], [], {"r1": _change(added=["200", "200"], removed=["100", "100"])}, AUDIT,
	)

	assert db.members_of("r1") == {"200"}
	assert db.audit_logs[0]["after"] == {"added": ["200"], "removed": ["100"]}


def test_patch_rejects_same_member_in_added_and_removed_and_rolls_back(db):
	db.add_role("r1", permissions=8)
	db.assign("r2", "100")

	with pytest.raises(RoleAssignmentChangeConflictError) as exc_info:
		manifest_repository.patch_manifest_db(
			[], [], [_role("r1", permissions=0)], [],
			{"r1": _change(added=["300"]), "r2": _change(added=["200", "100"], removed=["100", "200"])},
			AUDIT,
		)

	# 最初に見つかった 1 件（ロール ID・Discord ID の順）を返す
	assert (exc_info.value.role_id, exc_info.value.discord_id) == ("r2", "100")
	assert db.roles["r1"]["permissions"] == 8
	assert db.members_of("r1") == set()
	assert db.members_of("r2") == {"100"}
	assert db.audit_logs == []


def test_patch_assignments_leave_other_roles_untouched(db):
	db.assign("r1", "100")
	db.assign("r2", "100")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": _change(removed=["100"])})

	assert db.members_of("r1") == set()
	assert db.members_of("r2") == {"100"}


def test_patch_assignments_for_new_draft_role(db):
	# 同じ保存で作成したロール（仮 ID）にメンバーを割り当てられる
	manifest_repository.patch_manifest_db(
		[], [], [_role("draft-abc")], [], {"draft-abc": _change(added=["100"])}, AUDIT,
	)

	assert db.members_of("draft-abc") == {"100"}
	assignment_logs = [log for log in db.audit_logs if log["target_type"] == "role_assignment"]
	assert [(log["target_id"], log["after"]) for log in assignment_logs] == [
		("draft-abc", {"added": ["100"], "removed": []}),
	]


def test_replace_role_assignments_returns_actual_changes(db):
	db.assign("r1", "100", "200")

	with db.connect() as conn:
		with conn.cursor() as cur:
			changes = guild_repository.replace_role_assignments(cur, {"r1": ["200", "300"], "r2": []})

	assert changes == {"r1": (["300"], ["100"]), "r2": ([], [])}


def test_save_role_assignments_uses_diff_update(db):
	db.assign("r1", "100", "200")

	guild_repository.save_role_assignments({"r1": ["100", "300"]})

	assert db.members_of("r1") == {"100", "300"}
	assert len(_assignment_writes(db)) == 2


def test_replace_manifest_upserts_and_deletes_missing_rows(db):
	db.add_category("c1")
	db.add_category("c2")
	db.add_role("r1", category_id="c1")
	db.add_role("r2", category_id="c2")
	db.assign("r1", "100")

	manifest_repository.replace_manifest(
		[_category("c1", name="renamed")],
		[_role("r1", category_id="c1", permissions=8)],
		{"r1": ["100", "200"]},
	)

	assert set(db.categories) == {"c1"}
	assert db.categories["c1"]["name"] == "renamed"
	assert set(db.roles) == {"r1"}
	assert db.roles["r1"]["permissions"] == 8
	assert db.members_of("r1") == {"100", "200"}
	# 全件を削除して入れ直さない
	assert "DELETE FROM role_manifests" not in db.writes()
	assert "DELETE FROM role_categories" not in db.writes()


def test_replace_manifest_with_empty_payload_deletes_everything(db):
	db.add_category("c1")
	db.add_role("r1", category_id="c1")

	manifest_repository.replace_manifest([], [], {})

	assert db.categories == {}
	assert db.roles == {}


def test_replace_manifest_rolls_back_manifest_when_assignments_fail(db, monkeypatch):
	db.add_role("r1", permissions=8)

	def _fail(cur, assignments):
		raise RuntimeError("boom")

	monkeypatch.setattr(manifest_repository, "replace_role_assignments", _fail)

	with pytest.raises(RuntimeError):
		manifest_repository.replace_manifest([], [_role("r1", permissions=0)], {"r1": ["100"]})

	# マニフェストと割り当てを1つのトランザクションで保存する
	assert db.roles["r1"]["permissions"] == 8
