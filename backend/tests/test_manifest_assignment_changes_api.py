"""PATCH /api/v1/manifest の割当の差分形式（role_assignment_changes）のテスト（#228）

- 送ったメンバーだけを追加・削除する形で patch_manifest_db に渡す
- 同じメンバーを added と removed の両方に指定した場合は、Discord に問い合わせず 400 を返す
- added / removed が空のロールだけなら Discord に問い合わせない
- 廃止した upsert_role_assignments は 422 にする（割当を保存せずに成功しないようにする）
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.v1 import manifest as manifest_api
from app.core.auth import get_current_principal
from app.core.exceptions import RoleAssignmentChangeConflictError
from app.db.audit_repository import AuditContext, get_audit_context


@pytest.fixture
def client():
	main.app.dependency_overrides[get_current_principal] = lambda: {"sub": "sub-1", "discord_id": "111", "app_role": "admin"}
	main.app.dependency_overrides[get_audit_context] = lambda: AuditContext("fixed-req", "sub-1", "111")
	yield TestClient(main.app)
	main.app.dependency_overrides.clear()


@pytest.fixture
def saved(monkeypatch):
	calls = []
	monkeypatch.setattr(manifest_api, "patch_manifest_db", lambda *args, **kwargs: calls.append((args, kwargs)))
	return calls


@pytest.fixture
def fetch(monkeypatch):
	mock = AsyncMock(return_value=frozenset())
	monkeypatch.setattr(manifest_api, "fetch_protected_role_ids", mock)
	return mock


def test_patch_passes_changes_to_repository(client, saved, fetch):
	res = client.patch("/api/v1/manifest", json={"role_assignment_changes": {
		"r1": {"added": ["100"], "removed": ["200"]},
		"r2": {"removed": ["300"]},
	}})

	assert res.status_code == 200
	args, _kwargs = saved[0]
	# 省略した added / removed は空の配列として渡す
	assert args[4] == {
		"r1": {"added": ["100"], "removed": ["200"]},
		"r2": {"added": [], "removed": ["300"]},
	}
	fetch.assert_awaited_once()


def test_patch_rejects_same_member_in_added_and_removed(client, saved, fetch):
	res = client.patch("/api/v1/manifest", json={"role_assignment_changes": {
		"r1": {"added": ["100"], "removed": []},
		"r2": {"added": ["200", "100"], "removed": ["100", "200"]},
	}})

	assert res.status_code == 400
	assert res.json()["detail"] == {
		"code": "assignment_change_conflict",
		"message": "ロール r2 で、100 を追加と削除の両方に指定しています",
		"role_id": "r2",
		"discord_id": "100",
	}
	assert saved == []
	fetch.assert_not_awaited()


def test_patch_returns_400_when_repository_detects_conflict(client, fetch, monkeypatch):
	# API の検証をすり抜けてリポジトリ側で矛盾を検出した場合も、500 ではなく 400 にする
	def _raise(*_args, **_kwargs):
		raise RoleAssignmentChangeConflictError("r1", "100")

	monkeypatch.setattr(manifest_api, "patch_manifest_db", _raise)

	res = client.patch("/api/v1/manifest", json={"role_assignment_changes": {"r1": {"added": ["100"]}}})

	assert res.status_code == 400
	assert res.json()["detail"] == {
		"code": "assignment_change_conflict",
		"message": "ロール r1 で、100 を追加と削除の両方に指定しています",
		"role_id": "r1",
		"discord_id": "100",
	}


def test_patch_with_only_empty_changes_does_not_call_discord(client, saved, fetch):
	res = client.patch("/api/v1/manifest", json={"role_assignment_changes": {"r1": {"added": [], "removed": []}, "r2": {}}})

	assert res.status_code == 200
	assert saved[0][0][4] == {"r1": {"added": [], "removed": []}, "r2": {"added": [], "removed": []}}
	fetch.assert_not_awaited()


def test_patch_calls_discord_when_any_role_has_changes(client, saved, fetch):
	res = client.patch("/api/v1/manifest", json={"role_assignment_changes": {
		"r1": {"added": [], "removed": []},
		"r2": {"added": [], "removed": ["100"]},
	}})

	assert res.status_code == 200
	fetch.assert_awaited_once()


def test_patch_rejects_removed_upsert_role_assignments(client, saved, fetch):
	# 古い画面が全員分の形式で送っても、割当を保存しないまま 200 を返さない
	res = client.patch("/api/v1/manifest", json={"upsert_role_assignments": {"r1": ["100"]}})

	assert res.status_code == 422
	assert saved == []
	fetch.assert_not_awaited()


@pytest.mark.parametrize("change", [
	["100"],
	{"added": "100"},
	{"added": [100]},
	{"added": ["100"], "members": ["200"]},
])
def test_patch_rejects_malformed_change(client, saved, fetch, change):
	res = client.patch("/api/v1/manifest", json={"role_assignment_changes": {"r1": change}})

	assert res.status_code == 422
	assert saved == []
