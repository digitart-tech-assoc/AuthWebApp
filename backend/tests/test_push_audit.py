"""push（POST /api/v1/roles/push）の監査ログのテスト

Discord への変更は、API 呼び出しが成功するたびに記録し、記録に失敗しても push は続ける。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.v1 import roles as roles_api
from app.core.auth import get_current_principal
from app.db import audit_repository, guild_repository, manifest_repository
from app.db.audit_repository import AuditContext, get_audit_context
from tests.fake_role_db import FakeRoleDB

GUILD_ID = "1000"
AUDIT = AuditContext(request_id="req-push", actor_sub="sub-1", actor_discord_id="111", operation="push")


@pytest.fixture
def db(monkeypatch):
	"""監査ログの書き込み（record_audit_logs）と update_role_id をインメモリの DB に向ける。"""
	fake = FakeRoleDB()
	monkeypatch.setattr(audit_repository, "_connect", fake.connect)
	monkeypatch.setattr(manifest_repository, "_connect", fake.connect)
	monkeypatch.setattr(guild_repository, "_connect", fake.connect)
	return fake


def _discord_role(role_id, **kwargs):
	row = {
		"role_id": role_id, "name": "role", "color": "#000000", "hoist": False, "mentionable": False,
		"permissions": 0, "position": 1, "managed": False, "is_our_bot": False,
	}
	row.update(kwargs)
	return row


def _db_role(role_id, **kwargs):
	row = {
		"role_id": role_id, "name": "role", "color": "#000000", "hoist": False, "mentionable": False,
		"permissions": 0, "position": 1, "category_id": None, "is_our_bot": False,
	}
	row.update(kwargs)
	return row


async def _sync(desired, actual, *, created=None, edit_side_effect=None):
	with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
		patch.object(roles_api, "create_guild_role", new_callable=AsyncMock, return_value=created), \
		patch.object(roles_api, "edit_guild_role", new_callable=AsyncMock, side_effect=edit_side_effect) as edit, \
		patch.object(roles_api, "delete_guild_role", new_callable=AsyncMock), \
		patch.object(roles_api, "_log_push_error"):
		result = await roles_api._sync_role_definitions(desired, actual, "token", AUDIT)
	return result, edit


def _discord_logs(db):
	return [log for log in db.audit_logs if log["system"] == "discord"]


@pytest.mark.asyncio
async def test_update_keeps_discord_value_in_before(db):
	# 今回の事象の再現: Discord で直接変えた権限を、DB の古い値で上書きする
	result, _ = await _sync([_db_role("11", name="advisor", permissions=0)], [_discord_role("11", name="advisor", permissions=8)])

	assert result[0] == 1  # updated
	assert _discord_logs(db) == [{
		"request_id": "req-push", "operation": "push", "system": "discord",
		"target_type": "role", "target_id": "11", "action": "update",
		"before": {"permissions": 8}, "after": {"permissions": 0},
		"actor_sub": "sub-1", "actor_discord_id": "111",
	}]


@pytest.mark.asyncio
async def test_update_does_not_record_color_case_only_difference(db):
	await _sync(
		[_db_role("11", color="#99AAB5", permissions=0)],
		[_discord_role("11", color="#99aab5", permissions=8)],
	)

	log = _discord_logs(db)[0]
	assert "color" not in log["before"]
	assert "color" not in log["after"]


@pytest.mark.asyncio
async def test_failed_update_is_not_recorded(db):
	result, _ = await _sync(
		[_db_role("11", permissions=0)], [_discord_role("11", permissions=8)], edit_side_effect=RuntimeError("failed"),
	)

	assert result[6]  # errors
	assert db.audit_logs == []


@pytest.mark.asyncio
async def test_create_and_delete_record_full_definitions(db):
	created = {
		"role_id": "99", "name": "new", "color": "#112233", "hoist": True, "mentionable": False,
		"permissions": 0, "position": 2,
	}
	await _sync(
		[_db_role("new-role-without-draft", name="new")],
		[_discord_role("12", name="old", permissions=8, position=3)],
		created=created,
	)

	logs = {log["action"]: log for log in _discord_logs(db)}
	assert logs["create"]["target_id"] == "99"
	assert logs["create"]["before"] is None
	assert logs["create"]["after"] == {
		"name": "new", "color": "#112233", "hoist": True, "mentionable": False, "permissions": 0, "position": 2,
	}
	assert logs["delete"]["target_id"] == "12"
	assert logs["delete"]["before"] == {
		"name": "old", "color": "#000000", "hoist": False, "mentionable": False, "permissions": 8, "position": 3,
	}
	assert logs["delete"]["after"] is None


@pytest.mark.asyncio
async def test_db_and_discord_rows_share_request_id(db):
	db.add_role("draft-abc", name="new")
	created = {"role_id": "99", "name": "new", "color": "#000000", "hoist": False, "mentionable": False, "permissions": 0, "position": 1}

	await _sync([_db_role("draft-abc", name="new")], [], created=created)

	assert {(log["system"], log["action"]) for log in db.audit_logs} == {("discord", "create"), ("db", "rename_id")}
	assert {log["request_id"] for log in db.audit_logs} == {"req-push"}
	assert "99" in db.roles


@pytest.mark.asyncio
async def test_rename_id_failure_keeps_discord_create_row(db, monkeypatch):
	db.add_role("draft-abc", name="new")
	created = {"role_id": "99", "name": "new", "color": "#000000", "hoist": False, "mentionable": False, "permissions": 0, "position": 1}
	original_insert = audit_repository.insert_audit_logs

	def _fail_db_rows(cur, audit, logs):
		logs = list(logs)
		if any(log.system == "db" for log in logs):
			raise RuntimeError("audit insert failed")
		original_insert(cur, audit, logs)

	monkeypatch.setattr(manifest_repository, "insert_audit_logs", _fail_db_rows)

	result, _ = await _sync([_db_role("draft-abc", name="new")], [], created=created)

	# 仮 ID の置き換えは失敗し（DB は draft のまま）、Discord 側の作成の記録は残る
	assert "draft-abc" in db.roles
	assert result[6]
	assert [(log["system"], log["action"], log["target_id"]) for log in db.audit_logs] == [("discord", "create", "99")]


@pytest.mark.asyncio
async def test_discord_audit_failure_does_not_fail_push(db):
	db.fail_audit_insert = True

	result, edit = await _sync([_db_role("11", permissions=0)], [_discord_role("11", permissions=8)])

	edit.assert_awaited_once()
	assert result[0] == 1
	assert result[6] == []


# --- 並び替え ---

def _actual(*roles):
	by_id = {GUILD_ID: {"role_id": GUILD_ID, "position": 0}}
	for role_id, position in roles:
		by_id[role_id] = {"role_id": role_id, "position": position}
	return by_id


def _desired(*role_ids):
	return [{"role_id": GUILD_ID, "position": 0}] + [
		{"role_id": role_id, "position": index} for index, role_id in enumerate(role_ids, start=1)
	]


async def _reorder(desired, actual_by_id, created_real_ids=None):
	with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
		patch.object(roles_api, "reorder_guild_roles", new_callable=AsyncMock), \
		patch.object(roles_api, "_log_push_error"):
		return await roles_api._reorder_roles(desired, actual_by_id, created_real_ids or set(), "token", AUDIT)


@pytest.mark.asyncio
async def test_reorder_records_only_moved_roles(db):
	# 13 を一番下に動かした。11, 12 の相対的な順序は変わらない
	reordered, _ = await _reorder(_desired("13", "11", "12"), _actual(("11", 1), ("12", 2), ("13", 3)))

	assert reordered == 1
	assert [(log["target_id"], log["action"], log["before"], log["after"]) for log in db.audit_logs] == [
		("13", "reorder", {"position": 3}, {"position": 1}),
	]


@pytest.mark.asyncio
async def test_reorder_after_create_only_records_nothing(db):
	# ロールを作成すると既存ロールの position が一律にずれるが、並び順は変わっていない
	reordered, _ = await _reorder(
		_desired("11", "12", "99"), _actual(("11", 2), ("12", 3), ("99", 1)), created_real_ids={"99"},
	)

	assert reordered == 0
	assert db.audit_logs == []


@pytest.mark.asyncio
async def test_reorder_count_matches_recorded_rows(db):
	reordered, _ = await _reorder(
		_desired("15", "11", "14", "12", "13"),
		_actual(("11", 1), ("12", 2), ("13", 3), ("14", 4), ("15", 5)),
	)

	assert reordered == len(db.audit_logs) == 2


def test_moved_role_ids_is_deterministic():
	payload = [{"id": rid, "position": i} for i, rid in enumerate(["12", "11"], start=1)]
	actual = _actual(("11", 1), ("12", 2))

	results = {frozenset(roles_api._moved_role_ids(payload, actual, set())) for _ in range(5)}

	assert len(results) == 1
	assert len(next(iter(results))) == 1


# --- メンバーのロール ---

async def _member_diff(current_roles, db_roles, latest_roles=None):
	async def _fetch_member(_guild_id, user_id, _token, client=None):
		return {"user_id": user_id, "role_ids": list(latest_roles if latest_roles is not None else current_roles)}

	with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
		patch.object(roles_api, "fetch_role_assignments_for_user", return_value={rid: ["500"] for rid in db_roles}), \
		patch.object(roles_api, "fetch_guild_member", side_effect=_fetch_member), \
		patch.object(roles_api, "set_member_roles", new_callable=AsyncMock), \
		patch.object(roles_api, "add_role_to_member", new_callable=AsyncMock), \
		patch.object(roles_api, "remove_role_from_member", new_callable=AsyncMock):
		return await roles_api._apply_member_role_diff(
			"500", set(current_roles), {"11", "12", "13"}, "token", None, AUDIT,
		)


@pytest.mark.asyncio
async def test_member_single_add_is_recorded(db):
	assert await _member_diff([], ["11"]) == (1, 0)

	assert [(log["target_type"], log["target_id"], log["after"]) for log in db.audit_logs] == [
		("member_roles", "500", {"added": ["11"], "removed": []}),
	]


@pytest.mark.asyncio
async def test_member_patch_records_recomputed_diff(db):
	# PATCH の直前に取り直したロール（12 は既に付いている）で差分を計算し直す
	assert await _member_diff(["13"], ["11", "12"], latest_roles=["12", "13"]) == (1, 1)

	assert db.audit_logs[0]["after"] == {"added": ["11"], "removed": ["13"]}


@pytest.mark.asyncio
async def test_member_without_diff_records_nothing(db):
	assert await _member_diff(["11"], ["11"]) == (0, 0)

	assert db.audit_logs == []


# --- エンドポイント ---

def test_push_endpoint_passes_same_audit_context_to_each_step(monkeypatch):
	main.app.dependency_overrides[get_current_principal] = lambda: {"sub": "sub-1", "discord_id": "111", "app_role": "admin"}
	main.app.dependency_overrides[get_audit_context] = lambda: AuditContext("fixed-req", "sub-1", "111")
	sync = AsyncMock(return_value=(0, 0, 0, 0, set(), set(), [], {}, {}))
	reorder = AsyncMock(return_value=(0, []))
	assign = AsyncMock(return_value=(0, 0, 0, []))
	try:
		with patch.object(roles_api, "_get_token", return_value="token"), \
			patch.object(roles_api, "fetch_manifest", return_value={"roles": []}), \
			patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=[]), \
			patch.object(roles_api, "_sync_role_definitions", sync), \
			patch.object(roles_api, "_reorder_roles", reorder), \
			patch.object(roles_api, "_apply_role_assignment_diffs", assign), \
			patch.object(roles_api, "_notify_bot_to_reconcile", new_callable=AsyncMock, return_value=True):
			res = TestClient(main.app).post("/api/v1/roles/push")
	finally:
		main.app.dependency_overrides.clear()

	assert res.status_code == 200
	expected = AuditContext("fixed-req", "sub-1", "111", "push")
	assert sync.await_args.args[-1] == expected
	assert reorder.await_args.args[-1] == expected
	assert assign.await_args.args[-1] == expected
