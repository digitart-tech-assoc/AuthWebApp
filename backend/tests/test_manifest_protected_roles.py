"""Discord で直接付け外しするロール（③）の割当を、マニフェストの保存で変更できないことのテスト（#251）

- Bot より上のロール・managed ロールの割当が実際に変わる保存は 403 で拒否し、すべてロールバックする
- 割当が変わらない場合は拒否しない
- GET /manifest は会員種別のロールに membership_type を付けて返す
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.v1 import manifest as manifest_api
from app.api.v1 import roles as roles_api
from app.core.auth import get_current_principal
from app.core.exceptions import ProtectedRoleAssignmentError
from app.db import guild_repository, manifest_repository
from app.db.audit_repository import AuditContext, get_audit_context
from tests.fake_role_db import FakeRoleDB

AUDIT = AuditContext(request_id="req-1", actor_sub="sub-1", actor_discord_id="111", operation="manifest_patch")
GUILD_ID = "guild"
ADMIN_ROLE = "role-admin"
BOT_ROLE = "role-bot"


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


# --- リポジトリ ---

def test_patch_rejects_change_of_protected_role_and_rolls_back(db):
	db.add_role("r1", name="before")
	db.assign(ADMIN_ROLE, "100")

	with pytest.raises(ProtectedRoleAssignmentError):
		manifest_repository.patch_manifest_db(
			[], [], [_role("r1", name="after")], [], {ADMIN_ROLE: [], "role-game": ["200"]}, AUDIT,
			protected_role_ids=frozenset({ADMIN_ROLE}),
		)

	assert db.members_of(ADMIN_ROLE) == {"100"}
	assert db.members_of("role-game") == set()
	assert db.roles["r1"]["name"] == "before"
	assert db.audit_logs == []


def test_patch_allows_protected_role_without_actual_change(db):
	db.assign(ADMIN_ROLE, "100")

	manifest_repository.patch_manifest_db(
		[], [], [], [], {ADMIN_ROLE: ["100"], "role-game": ["200"]}, AUDIT,
		protected_role_ids=frozenset({ADMIN_ROLE}),
	)

	assert db.members_of("role-game") == {"200"}


def test_put_rejects_change_of_protected_role(db):
	with pytest.raises(ProtectedRoleAssignmentError):
		manifest_repository.replace_manifest(
			[], [], {BOT_ROLE: ["100"]}, AUDIT, protected_role_ids=frozenset({BOT_ROLE}),
		)

	assert db.members_of(BOT_ROLE) == set()


# --- 対象のロールの判定 ---

def _discord_role(role_id, position, managed=False):
	return {"role_id": role_id, "name": role_id, "position": position, "managed": managed}


async def _protected(roles, bot_member):
	with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
		patch.object(roles_api, "DISCORD_TOKEN", "token"), \
		patch.object(roles_api, "fetch_guild_roles", AsyncMock(return_value=roles)), \
		patch.object(roles_api, "fetch_bot_guild_member", AsyncMock(return_value=bot_member)):
		return await roles_api.fetch_protected_role_ids()


@pytest.mark.asyncio
async def test_protected_roles_are_roles_bot_cannot_manage():
	roles = [
		_discord_role(GUILD_ID, 0),
		_discord_role("role-game", 1),
		_discord_role("role-member", 2),
		_discord_role("role-integration", 3, managed=True),
		_discord_role(BOT_ROLE, 4),
		_discord_role(ADMIN_ROLE, 5),
	]

	protected = await _protected(roles, {"user_id": "bot", "role_ids": [BOT_ROLE, "role-integration"]})

	assert protected == {GUILD_ID, "role-integration", BOT_ROLE, ADMIN_ROLE}


@pytest.mark.asyncio
async def test_all_roles_are_protected_when_bot_role_is_unknown():
	roles = [_discord_role("role-game", 1), _discord_role(ADMIN_ROLE, 5)]

	protected = await _protected(roles, None)

	assert protected == {"role-game", ADMIN_ROLE}


# --- エンドポイント ---

@pytest.fixture
def client():
	main.app.dependency_overrides[get_current_principal] = lambda: {"sub": "sub-1", "discord_id": "111", "app_role": "admin"}
	main.app.dependency_overrides[get_audit_context] = lambda: AuditContext("fixed-req", "sub-1", "111")
	yield TestClient(main.app)
	main.app.dependency_overrides.clear()


def _raise_protected(*_args, **_kwargs):
	raise ProtectedRoleAssignmentError(ADMIN_ROLE)


def test_patch_endpoint_returns_403_for_protected_role(client, monkeypatch):
	monkeypatch.setattr(manifest_api, "fetch_protected_role_ids", AsyncMock(return_value=frozenset({ADMIN_ROLE})))
	monkeypatch.setattr(manifest_api, "patch_manifest_db", _raise_protected)

	res = client.patch("/api/v1/manifest", json={"upsert_role_assignments": {ADMIN_ROLE: []}})

	assert res.status_code == 403
	assert res.json()["detail"] == {
		"code": "protected_role_assignment",
		"message": f"ロール {ADMIN_ROLE} は Discord で直接付け外しするロールのため、割当を変更できません",
	}


def test_put_endpoint_returns_403_for_protected_role(client, monkeypatch):
	monkeypatch.setattr(manifest_api, "fetch_protected_role_ids", AsyncMock(return_value=frozenset({ADMIN_ROLE})))
	monkeypatch.setattr(manifest_api, "replace_manifest", _raise_protected)

	res = client.put("/api/v1/manifest", json={"role_assignments": {ADMIN_ROLE: []}})

	assert res.status_code == 403


def test_patch_endpoint_passes_protected_role_ids(client, monkeypatch):
	calls = []
	monkeypatch.setattr(manifest_api, "fetch_protected_role_ids", AsyncMock(return_value=frozenset({ADMIN_ROLE})))
	monkeypatch.setattr(manifest_api, "patch_manifest_db", lambda *args, **kwargs: calls.append(kwargs))

	res = client.patch("/api/v1/manifest", json={"upsert_role_assignments": {"role-game": ["100"]}})

	assert res.status_code == 200
	assert calls == [{"protected_role_ids": frozenset({ADMIN_ROLE})}]


def test_patch_without_assignments_does_not_call_discord(client, monkeypatch):
	fetch = AsyncMock(return_value=frozenset())
	monkeypatch.setattr(manifest_api, "fetch_protected_role_ids", fetch)
	monkeypatch.setattr(manifest_api, "patch_manifest_db", lambda *args, **kwargs: None)

	res = client.patch("/api/v1/manifest", json={"upsert_roles": [_role("r1")]})

	assert res.status_code == 200
	fetch.assert_not_awaited()


def test_patch_endpoint_returns_502_when_discord_fetch_fails(client, monkeypatch):
	saved = []
	monkeypatch.setattr(roles_api, "DISCORD_TOKEN", "token")
	monkeypatch.setattr(roles_api, "fetch_guild_roles", AsyncMock(side_effect=RuntimeError("boom")))
	monkeypatch.setattr(roles_api, "fetch_bot_guild_member", AsyncMock(return_value=None))
	monkeypatch.setattr(manifest_api, "patch_manifest_db", lambda *args, **kwargs: saved.append(args))

	res = client.patch("/api/v1/manifest", json={"upsert_role_assignments": {"role-game": ["100"]}})

	assert res.status_code == 502
	assert res.json()["detail"]["code"] == "discord_unavailable"
	assert saved == []


def test_patch_endpoint_returns_502_when_bot_member_fetch_fails(client, monkeypatch):
	monkeypatch.setattr(roles_api, "DISCORD_TOKEN", "token")
	monkeypatch.setattr(roles_api, "fetch_guild_roles", AsyncMock(return_value=[]))
	monkeypatch.setattr(roles_api, "fetch_bot_guild_member", AsyncMock(side_effect=RuntimeError("boom")))
	monkeypatch.setattr(manifest_api, "patch_manifest_db", lambda *args, **kwargs: pytest.fail("must not save"))

	res = client.patch("/api/v1/manifest", json={"upsert_role_assignments": {"role-game": ["100"]}})

	assert res.status_code == 502
	assert res.json()["detail"]["code"] == "discord_unavailable"


def test_protected_role_is_rejected_before_membership_update(db, monkeypatch):
	# 保護対象の拒否は、会員種別の更新より先に効く（admin ロールの割当の変更で種別の行が変わらない）
	monkeypatch.setenv("MEMBER_ROLE_IDS", "role-member")
	db.add_membership("100", "member")
	db.assign("role-member", "100")

	with pytest.raises(ProtectedRoleAssignmentError):
		manifest_repository.patch_manifest_db(
			[], [], [], [], {"role-member": [], ADMIN_ROLE: ["100"]}, AUDIT,
			protected_role_ids=frozenset({ADMIN_ROLE}),
		)

	assert db.membership_types_of("100") == {"member"}
	assert db.members_of("role-member") == {"100"}


def test_get_manifest_returns_membership_type(client, monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", "role-member")
	monkeypatch.setenv("ADMIN_ROLE_IDS", ADMIN_ROLE)
	monkeypatch.setattr(manifest_api, "fetch_manifest", lambda: {
		"categories": [],
		"roles": [_role("role-member"), _role(ADMIN_ROLE), _role("role-game")],
	})

	res = client.get("/api/v1/manifest")

	assert res.status_code == 200
	types = {r["role_id"]: r["membership_type"] for r in res.json()["roles"]}
	assert types == {"role-member": "member", ADMIN_ROLE: "admin", "role-game": None}
