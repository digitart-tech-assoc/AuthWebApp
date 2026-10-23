"""マニフェスト保存（PATCH / PUT）と仮 ID の置き換えの監査ログのテスト"""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.v1 import manifest as manifest_api
from app.core.auth import get_current_principal
from app.db import guild_repository, manifest_repository
from app.db.audit_repository import AuditContext, get_audit_context
from tests.fake_role_db import AuditInsertError, FakeRoleDB

AUDIT = AuditContext(request_id="req-1", actor_sub="sub-1", actor_discord_id="111", operation="manifest_patch")


@pytest.fixture
def db(monkeypatch):
	fake = FakeRoleDB()
	monkeypatch.setattr(manifest_repository, "_connect", fake.connect)
	monkeypatch.setattr(guild_repository, "_connect", fake.connect)
	return fake


def _role(role_id, **kwargs):
	row = {
		"role_id": role_id, "name": "role", "color": "#000000", "hoist": False, "mentionable": False,
		"permissions": 0, "position": 1, "category_id": None, "is_our_bot": False,
	}
	row.update(kwargs)
	return row


def _category(id, **kwargs):
	row = {"id": id, "name": "cat", "display_order": 0, "is_collapsed": False, "permissions": 0, "is_restricted": False}
	row.update(kwargs)
	return row


def _logs(db, **filters):
	return [log for log in db.audit_logs if all(log[k] == v for k, v in filters.items())]


def _patch(roles=(), delete_roles=(), categories=(), delete_categories=(), assignments=None, audit=AUDIT):
	manifest_repository.patch_manifest_db(
		list(categories), list(delete_categories), list(roles), list(delete_roles), assignments or {}, audit,
	)


# --- PATCH ---

def test_patch_records_only_changed_fields_with_context(db):
	db.add_role("r1", name="advisor", permissions=8)

	_patch(roles=[_role("r1", name="advisor", permissions=0)])

	assert db.audit_logs == [{
		"request_id": "req-1", "operation": "manifest_patch", "system": "db",
		"target_type": "role", "target_id": "r1", "action": "update",
		"before": {"permissions": 8}, "after": {"permissions": 0},
		"actor_sub": "sub-1", "actor_discord_id": "111",
	}]


def test_patch_without_changes_records_nothing(db):
	db.add_role("r1", name="advisor", permissions=8)
	db.assign("r1", "100")

	_patch(roles=[_role("r1", name="advisor", permissions=8)], assignments={"r1": ["100"]})

	assert db.audit_logs == []


def test_patch_records_create_and_delete(db):
	db.add_role("r1", name="old")

	_patch(roles=[_role("draft-abc", name="new")], delete_roles=["r1"], categories=[_category("c1")])

	created = _logs(db, target_id="draft-abc")[0]
	assert created["action"] == "create"
	assert created["before"] is None
	assert created["after"]["name"] == "new"
	deleted = _logs(db, target_id="r1")[0]
	assert deleted["action"] == "delete"
	assert deleted["before"]["name"] == "old"
	assert deleted["after"] is None
	assert _logs(db, target_type="category")[0]["action"] == "create"


def test_patch_records_category_id_set_null_by_category_delete(db):
	db.add_category("c1")
	db.add_role("r1", category_id="c1")

	_patch(delete_categories=["c1"])

	assert db.roles["r1"]["category_id"] is None
	role_logs = _logs(db, target_type="role")
	assert role_logs == [{
		**role_logs[0],
		"target_id": "r1", "action": "update",
		"before": {"category_id": "c1"}, "after": {"category_id": None},
	}]
	assert _logs(db, target_type="category")[0]["action"] == "delete"


def test_patch_merges_set_null_and_upsert_into_one_row(db):
	db.add_category("c1")
	db.add_category("c2")
	db.add_role("r1", category_id="c1")

	_patch(roles=[_role("r1", category_id="c2")], delete_categories=["c1"])

	role_logs = _logs(db, target_type="role")
	assert len(role_logs) == 1
	assert role_logs[0]["before"] == {"category_id": "c1"}
	assert role_logs[0]["after"] == {"category_id": "c2"}


def test_patch_records_only_added_and_removed_members(db):
	db.add_role("r1")
	db.assign("r1", "100", "200")

	_patch(assignments={"r1": ["200", "300"]})

	assert _logs(db, target_type="role_assignment") == [{
		**_logs(db, target_type="role_assignment")[0],
		"target_id": "r1", "action": "update", "before": None,
		"after": {"added": ["300"], "removed": ["100"]},
	}]


def test_patch_rolls_back_when_audit_insert_fails(db):
	db.add_role("r1", permissions=8)
	db.assign("r1", "100")
	db.fail_audit_insert = True

	with pytest.raises(AuditInsertError):
		_patch(roles=[_role("r1", permissions=0)], assignments={"r1": []})

	assert db.roles["r1"]["permissions"] == 8
	assert db.members_of("r1") == {"100"}


def test_patch_without_audit_context_records_nothing(db):
	db.add_role("r1", permissions=8)

	_patch(roles=[_role("r1", permissions=0)], audit=None)

	assert db.roles["r1"]["permissions"] == 0
	assert db.audit_logs == []


def test_patch_locks_rows_before_change(db):
	db.add_role("r1")

	_patch(roles=[_role("r1", name="renamed")])

	first_write = next(i for i, sql in enumerate(db.executed) if not sql.startswith("SELECT"))
	locked = [sql for sql in db.executed[:first_write] if sql.endswith("FOR UPDATE")]
	assert any("FROM role_manifests" in sql for sql in locked)
	assert any("FROM role_categories" in sql for sql in locked)


def test_patch_audit_does_not_contain_member_names(db):
	db.add_role("r1")

	_patch(assignments={"r1": ["100"]})

	assert "username" not in str(db.audit_logs)
	assert "display_name" not in str(db.audit_logs)


def test_patch_records_color_case_change(db):
	db.add_role("r1", color="#99AAB5")

	_patch(roles=[_role("r1", color="#99aab5")])

	assert _logs(db, target_id="r1")[0]["before"] == {"color": "#99AAB5"}
	assert _logs(db, target_id="r1")[0]["after"] == {"color": "#99aab5"}


# --- PUT ---

def test_put_records_only_actual_changes(db):
	db.add_category("c1")
	db.add_role("keep", name="same", category_id="c1")
	db.add_role("change", permissions=8)
	db.add_role("gone")
	db.assign("keep", "100")
	audit = AUDIT.with_operation("manifest_put")

	manifest_repository.replace_manifest(
		[_category("c1")],
		[_role("keep", name="same", category_id="c1"), _role("change", permissions=0), _role("new")],
		{"keep": ["100"]},
		audit,
	)

	assert {(log["target_id"], log["action"]) for log in db.audit_logs} == {
		("change", "update"), ("gone", "delete"), ("new", "create"),
	}
	assert all(log["operation"] == "manifest_put" for log in db.audit_logs)


def test_put_rolls_back_when_audit_insert_fails(db):
	db.add_role("r1", permissions=8)
	db.fail_audit_insert = True

	with pytest.raises(AuditInsertError):
		manifest_repository.replace_manifest([], [_role("r1", permissions=0)], {}, AUDIT)

	assert db.roles["r1"]["permissions"] == 8


# --- update_role_id ---

def test_update_role_id_records_rename_in_one_row(db):
	db.add_role("draft-abc")
	db.assign("draft-abc", "100")

	manifest_repository.update_role_id("draft-abc", "999", AUDIT.with_operation("push"))

	assert db.members_of("999") == {"100"}
	assert len(db.audit_logs) == 1
	log = db.audit_logs[0]
	assert (log["target_type"], log["target_id"], log["action"]) == ("role", "999", "rename_id")
	assert log["before"] == {"role_id": "draft-abc"}
	assert log["after"] == {"role_id": "999"}


def test_update_role_id_rolls_back_when_audit_insert_fails(db):
	db.add_role("draft-abc")
	db.assign("draft-abc", "100")
	db.fail_audit_insert = True

	with pytest.raises(AuditInsertError):
		manifest_repository.update_role_id("draft-abc", "999", AUDIT)

	assert "draft-abc" in db.roles
	assert db.members_of("draft-abc") == {"100"}


# --- エンドポイント ---

@pytest.fixture
def client():
	main.app.dependency_overrides[get_current_principal] = lambda: {"sub": "sub-1", "discord_id": "111", "app_role": "admin"}
	main.app.dependency_overrides[get_audit_context] = lambda: AuditContext("fixed-req", "sub-1", "111")
	yield TestClient(main.app)
	main.app.dependency_overrides.clear()


def test_patch_endpoint_passes_audit_context(client, monkeypatch):
	calls = []
	monkeypatch.setattr(manifest_api, "patch_manifest_db", lambda *args: calls.append(args))

	res = client.patch("/api/v1/manifest", json={"upsert_roles": [_role("r1")]})

	assert res.status_code == 200
	assert calls[0][-1] == AuditContext("fixed-req", "sub-1", "111", "manifest_patch")


def test_put_endpoint_passes_audit_context(client, monkeypatch):
	calls = []
	monkeypatch.setattr(manifest_api, "replace_manifest", lambda *args: calls.append(args))

	res = client.put("/api/v1/manifest", json={"roles": [_role("r1")]})

	assert res.status_code == 200
	assert calls[0][-1] == AuditContext("fixed-req", "sub-1", "111", "manifest_put")
