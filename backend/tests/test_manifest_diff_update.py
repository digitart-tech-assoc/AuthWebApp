"""マニフェスト・割り当ての保存を差分更新にしたことのテスト"""

import pytest

from app.db import guild_repository, manifest_repository
from tests.fake_role_db import FakeRoleDB


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


def test_patch_assignments_only_touches_added_and_removed_members(db):
	db.add_role("r1")
	db.assign("r1", "100", "200", "300")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": ["200", "300", "400"]})

	assert db.members_of("r1") == {"200", "300", "400"}
	writes = _assignment_writes(db)
	# 一覧に残ったメンバー（200, 300）は DELETE・INSERT しない
	assert len(writes) == 2
	assert writes[0].startswith("DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s")
	assert writes[1].startswith("INSERT INTO role_member_assignments")
	assert not any(sql == "DELETE FROM role_member_assignments WHERE role_id = %s" for sql in writes)


def test_patch_assignments_with_same_members_writes_nothing(db):
	db.add_role("r1")
	db.assign("r1", "100", "200")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": ["200", "100"]})

	assert db.members_of("r1") == {"100", "200"}
	assert _assignment_writes(db) == []


def test_patch_assignments_leave_other_roles_untouched(db):
	db.assign("r1", "100")
	db.assign("r2", "100")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": []})

	assert db.members_of("r1") == set()
	assert db.members_of("r2") == {"100"}


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
