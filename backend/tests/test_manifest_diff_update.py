"""マニフェスト・割り当ての保存を差分更新にしたことのテスト"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.v1 import manifest as manifest_api
from app.core.auth import get_current_principal
from app.core.exceptions import RoleAssignmentChangeConflictError
from app.db import guild_repository, manifest_repository
from app.db.audit_repository import AuditContext, get_audit_context
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

	manifest_repository.patch_manifest_db(
		[], [], [], [], {"r1": {"added": ["400"], "removed": ["100"]}},
	)

	assert db.members_of("r1") == {"200", "300", "400"}
	writes = _assignment_writes(db)
	# 一覧に残ったメンバー（200, 300）は DELETE・INSERT しない
	assert len(writes) == 2
	assert writes[0].startswith("DELETE FROM role_member_assignments WHERE role_id = %s AND user_id = %s")
	assert writes[1].startswith("INSERT INTO role_member_assignments")
	assert not any(sql == "DELETE FROM role_member_assignments WHERE role_id = %s" for sql in writes)


def test_patch_assignments_with_empty_added_and_removed_writes_nothing(db):
	db.add_role("r1")
	db.assign("r1", "100", "200")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": {"added": [], "removed": []}})

	assert db.members_of("r1") == {"100", "200"}
	assert _assignment_writes(db) == []


def test_patch_assignments_leave_other_roles_untouched(db):
	db.assign("r1", "100")
	db.assign("r2", "100")

	manifest_repository.patch_manifest_db([], [], [], [], {"r1": {"added": [], "removed": ["100"]}})

	assert db.members_of("r1") == set()
	assert db.members_of("r2") == {"100"}


def test_patch_preserves_assignment_added_by_self_batch(db):
	"""画面を開いた後に self-batch で付けた割り当てが、管理者の保存で外れないこと（#228）。"""
	db.add_role("r1")
	db.assign("r1", "100", "200")

	# 管理者が画面を開いた後に、メンバー 300 が self-batch で r1 を自分に付与する
	guild_repository.batch_update_user_roles("300", ["r1"], [])
	assert db.members_of("r1") == {"100", "200", "300"}

	# 管理者は画面上の操作（100 を外し 400 を追加）だけを差分として保存する
	manifest_repository.patch_manifest_db(
		[], [], [], [], {"r1": {"added": ["400"], "removed": ["100"]}},
	)

	assert db.members_of("r1") == {"200", "300", "400"}


def test_patch_preserves_concurrent_admin_changes(db):
	"""管理者2人が同じロールの別メンバーを編集しても、互いの変更を上書きしないこと（#228）。"""
	db.add_role("r1")
	db.assign("r1", "100", "200")

	# 管理者A: 300 を追加して保存
	manifest_repository.patch_manifest_db([], [], [], [], {"r1": {"added": ["300"], "removed": []}})
	# 管理者B: 200 を削除し 400 を追加して保存
	manifest_repository.patch_manifest_db([], [], [], [], {"r1": {"added": ["400"], "removed": ["200"]}})

	assert db.members_of("r1") == {"100", "300", "400"}


def test_apply_role_assignment_changes_returns_actual_changes_and_deduplicates(db):
	db.assign("r1", "100", "200")

	with db.connect() as conn:
		with conn.cursor() as cur:
			changes = guild_repository.apply_role_assignment_changes(
				cur,
				{
					"r1": {"added": ["200", "300", "300"], "removed": ["100", "100", "999"]},
					"r2": {"added": [], "removed": []},
				},
			)

	assert changes == {"r1": (["300"], ["100"]), "r2": ([], [])}
	assert db.members_of("r1") == {"200", "300"}


def test_patch_rejects_same_member_in_added_and_removed_and_rolls_back(db):
	db.add_role("r1", name="before")
	db.assign("r1", "100")
	db.assign("r2", "200")

	with pytest.raises(RoleAssignmentChangeConflictError) as exc_info:
		manifest_repository.patch_manifest_db(
			[], [], [_role("r1", name="after")], [],
			{
				"r1": {"added": ["100", "300"], "removed": ["100"]},
				"r2": {"added": ["400"], "removed": ["200"]},
			},
		)

	assert (exc_info.value.role_id, exc_info.value.discord_id) == ("r1", "100")
	assert db.roles["r1"]["name"] == "before"
	assert db.members_of("r1") == {"100"}
	assert db.members_of("r2") == {"200"}


@pytest.fixture
def client():
	main.app.dependency_overrides[get_current_principal] = lambda: {"sub": "sub-1", "discord_id": "111", "app_role": "admin"}
	main.app.dependency_overrides[get_audit_context] = lambda: AuditContext("fixed-req", "sub-1", "111")
	yield TestClient(main.app)
	main.app.dependency_overrides.clear()


def test_patch_endpoint_returns_400_on_conflicting_member_without_calling_discord(client, monkeypatch):
	fetch = AsyncMock(return_value=frozenset())
	monkeypatch.setattr(manifest_api, "fetch_protected_role_ids", fetch)
	monkeypatch.setattr(manifest_api, "patch_manifest_db", lambda *args, **kwargs: pytest.fail("must not save"))

	res = client.patch(
		"/api/v1/manifest",
		json={"role_assignment_changes": {"r1": {"added": ["100"], "removed": ["100"]}}},
	)

	assert res.status_code == 400
	assert res.json()["detail"] == {
		"code": "role_assignment_change_conflict",
		"message": "ロール r1 のメンバー 100 を追加と削除の両方に指定することはできません",
		"role_id": "r1",
		"discord_id": "100",
	}
	fetch.assert_not_awaited()


def test_patch_endpoint_with_empty_role_changes_does_not_call_discord(client, monkeypatch):
	fetch = AsyncMock(return_value=frozenset())
	monkeypatch.setattr(manifest_api, "fetch_protected_role_ids", fetch)
	monkeypatch.setattr(manifest_api, "patch_manifest_db", lambda *args, **kwargs: None)

	res = client.patch(
		"/api/v1/manifest",
		json={"role_assignment_changes": {"r1": {"added": [], "removed": []}}},
	)

	assert res.status_code == 200
	fetch.assert_not_awaited()


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
