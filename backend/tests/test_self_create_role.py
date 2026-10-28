"""member によるロール作成（POST /api/v1/roles/self-create）のテスト（#227）"""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1 import roles as roles_api
from app.core.auth import require_member
from app.core.config import MEMBERSHIP_ROLE_NAMES, ROLE_SELF_CREATE_RATE_LIMIT
from app.db import audit_repository, guild_repository, manifest_repository
from app.db.audit_repository import AuditContext
from app.db.manifest_repository import normalize_role_name
from tests.fake_role_db import FakeRoleDB

CREATOR = {"sub": "sub-1", "discord_id": "500", "app_role": "member"}
OTHER_MEMBER = {"sub": "sub-2", "discord_id": "600", "app_role": "member"}
NEW_ROLE_ID = "900"


@pytest.fixture
def db(monkeypatch):
	fake = FakeRoleDB()
	for module in (audit_repository, guild_repository, manifest_repository):
		monkeypatch.setattr(module, "_connect", fake.connect)
	fake.add_category("cat-game", "ゲーム")
	fake.add_category("cat-skill", "スキル")
	fake.add_category("cat-info", "会員情報", is_restricted=True)
	# 予約名だが is_restricted が付いていないカテゴリ
	fake.add_category("cat-grade", "学年")
	fake.add_role("11", "Minecraft", category_id="cat-game", position=3)
	fake.add_role("12", "Python", category_id="cat-skill", position=2)
	return fake


def _manifest(db: FakeRoleDB) -> dict:
	return {"categories": list(db.categories.values()), "roles": list(db.roles.values())}


def _audit() -> AuditContext:
	return AuditContext("req-1", "sub-1", "500")


def _payload(**kwargs) -> roles_api.SelfCreateRolePayload:
	return roles_api.SelfCreateRolePayload(**{"name": "Splatoon", "color": "#3498DB", "category_id": "cat-game", **kwargs})


def _created(payload: dict) -> dict:
	"""create_guild_role の戻り値（Discord の応答を変換した形）"""
	return {
		"role_id": NEW_ROLE_ID, "name": payload["name"], "color": "#3498db", "hoist": payload["hoist"],
		"mentionable": payload["mentionable"], "permissions": int(payload["permissions"]), "position": 1,
	}


class _Discord:
	"""roles_api が呼ぶ Discord API のモックをまとめる"""

	def __init__(self, *, create_error=None, add_error=None):
		self.create = AsyncMock(side_effect=create_error or (lambda guild_id, token, payload: _created(payload)))
		self.delete = AsyncMock()
		self.add = AsyncMock(side_effect=add_error)
		self.remove = AsyncMock()

	def patches(self, db: FakeRoleDB):
		return [
			patch.object(roles_api, "_get_token", return_value="token"),
			patch.object(roles_api, "fetch_manifest", side_effect=lambda: _manifest(db)),
			patch.object(roles_api, "create_guild_role", new=self.create),
			patch.object(roles_api, "delete_guild_role", new=self.delete),
			patch.object(roles_api, "add_role_to_member", new=self.add),
			patch.object(roles_api, "remove_role_from_member", new=self.remove),
		]


async def _self_create(db, discord: _Discord | None = None, payload=None, principal=CREATOR):
	discord = discord or _Discord()
	patches = discord.patches(db)
	for p in patches:
		p.start()
	try:
		return await roles_api.self_create_role(payload or _payload(), principal, audit=_audit())
	finally:
		for p in reversed(patches):
			p.stop()


def _summary(db):
	return [(log["operation"], log["system"], log["target_type"], log["target_id"], log["action"]) for log in db.audit_logs]


# --- 認可・入力 ---

def test_self_create_is_member_scoped():
	dependency = inspect.signature(roles_api.self_create_role).parameters["_principal"].default.dependency
	assert dependency is require_member


@pytest.mark.parametrize("kwargs", [
	{"name": ""},
	{"name": "   "},
	{"name": "x" * 101},
	{"color": "blue"},
	{"color": "#12345"},
	{"category_id": ""},
])
def test_invalid_payload_is_rejected(kwargs):
	with pytest.raises(ValidationError):
		_payload(**kwargs)


def test_payload_does_not_accept_permissions():
	payload = _payload(permissions=8, hoist=True)
	assert not hasattr(payload, "permissions")
	assert _payload(name="  Splatoon  ").name == "Splatoon"


@pytest.mark.asyncio
async def test_missing_discord_id_is_rejected(db):
	discord = _Discord()
	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord, principal={"sub": "sub-1", "app_role": "member"})
	assert exc_info.value.status_code == 400
	discord.create.assert_not_called()


@pytest.mark.parametrize("category_id", ["cat-info", "cat-grade", "cat-unknown"])
@pytest.mark.asyncio
async def test_restricted_or_unknown_category_is_rejected(db, category_id):
	discord = _Discord()
	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord, _payload(category_id=category_id))
	assert exc_info.value.status_code == 403
	discord.create.assert_not_called()
	assert NEW_ROLE_ID not in db.roles


@pytest.mark.asyncio
async def test_category_without_restricted_flag_is_rejected(db):
	# フラグが欠けたカテゴリは拒否側に倒す
	del db.categories["cat-game"]["is_restricted"]
	discord = _Discord()
	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord)
	assert exc_info.value.status_code == 403
	discord.create.assert_not_called()


@pytest.mark.parametrize("name", ["Minecraft", " minecraft ", "MINECRAFT"])
@pytest.mark.asyncio
async def test_duplicate_name_is_rejected(db, name):
	discord = _Discord()
	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord, _payload(name=name))
	assert exc_info.value.status_code == 409
	discord.create.assert_not_called()


@pytest.mark.parametrize("name", [
	"administrator", "Administrator", "ADMINISTRATOR", " 管理者 ",
	"member", "会員", "OBOG", "OB/OG", "ob-og", "pre-member", "sub垢",
])
@pytest.mark.asyncio
async def test_reserved_role_name_is_rejected(db, name):
	# /members/sync がロール名で admin などを判定するため、予約名のロールは作らせない
	discord = _Discord()
	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord, _payload(name=name))
	assert exc_info.value.status_code == 409
	discord.create.assert_not_called()
	assert NEW_ROLE_ID not in db.roles


def test_reserved_names_cover_all_names_matched_by_sync():
	# /members/sync が会員種別の判定に使う名前は、すべて作成を拒否する
	names = sorted({name for names in MEMBERSHIP_ROLE_NAMES.values() for name in names})
	roles = [{"role_id": str(i), "name": name} for i, name in enumerate(names)]

	matched = roles_api._match_role_ids(roles)

	assert len(matched["all_matched_role_ids"]) == len(names)
	assert {normalize_role_name(name) for name in names} <= roles_api._RESERVED_ROLE_NAME_KEYS


# --- 正常系 ---

@pytest.mark.asyncio
async def test_creates_role_without_permissions_and_assigns_creator(db):
	discord = _Discord()

	result = await _self_create(db, discord)

	sent = discord.create.call_args.args[2]
	assert sent["permissions"] == "0"
	assert (sent["hoist"], sent["mentionable"]) == (False, True)
	assert result["ok"] is True
	assert result["assigned"] is True
	assert result["role"]["role_id"] == NEW_ROLE_ID
	saved = db.roles[NEW_ROLE_ID]
	assert (saved["name"], saved["color"], saved["permissions"], saved["category_id"]) == ("Splatoon", "#3498DB", 0, "cat-game")
	# 既存ロールの最小 position の1つ下（1 未満にはしない）
	assert saved["position"] == 1
	discord.add.assert_awaited_once_with(roles_api.DISCORD_GUILD_ID, "500", NEW_ROLE_ID, "token")
	assert db.members_of(NEW_ROLE_ID) == {"500"}
	assert _summary(db) == [
		("self_create", "discord", "role", NEW_ROLE_ID, "create"),
		("self_create", "db", "role", NEW_ROLE_ID, "create"),
		("self_create", "discord", "member_roles", "500", "update"),
		("self_create", "db", "member_roles", "500", "update"),
	]


@pytest.mark.asyncio
async def test_created_role_can_be_self_assigned_by_other_member(db):
	await _self_create(db)

	discord_roles = [
		{"role_id": "11", "position": 3, "managed": False},
		{"role_id": "12", "position": 2, "managed": False},
		{"role_id": NEW_ROLE_ID, "position": 1, "managed": False},
		{"role_id": "role-bot", "position": 10, "managed": True},
	]
	with patch.object(roles_api, "_get_token", return_value="token"), \
		patch.object(roles_api, "fetch_manifest", side_effect=lambda: _manifest(db)), \
		patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=discord_roles), \
		patch.object(roles_api, "fetch_guild_member", new_callable=AsyncMock, return_value={"role_ids": []}), \
		patch.object(roles_api, "fetch_bot_guild_member", new_callable=AsyncMock, return_value={"role_ids": ["role-bot"]}), \
		patch.object(roles_api, "fetch_role_ids_with_channel_permissions", new_callable=AsyncMock, return_value=set()), \
		patch.object(roles_api, "set_member_roles", new_callable=AsyncMock):
		result = await roles_api.self_batch_roles(
			roles_api.SelfBatchPayload(roles_to_add=[NEW_ROLE_ID]),
			OTHER_MEMBER,
			audit=AuditContext("req-2", "sub-2", "600"),
		)

	assert result["added"] == [NEW_ROLE_ID]
	assert db.members_of(NEW_ROLE_ID) == {"500", "600"}


# --- 失敗時 ---

@pytest.mark.asyncio
async def test_discord_create_failure_returns_502_and_saves_nothing(db):
	discord = _Discord(create_error=Exception("boom"))
	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord)
	assert exc_info.value.status_code == 502
	assert NEW_ROLE_ID not in db.roles
	discord.add.assert_not_called()


@pytest.mark.asyncio
async def test_db_failure_deletes_discord_role(db):
	db.fail_audit_insert = True
	discord = _Discord()

	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord)

	assert exc_info.value.status_code == 500
	assert "deleted" in exc_info.value.detail
	discord.delete.assert_awaited_once_with(roles_api.DISCORD_GUILD_ID, NEW_ROLE_ID, "token")
	assert NEW_ROLE_ID not in db.roles
	discord.add.assert_not_called()


@pytest.mark.asyncio
async def test_db_failure_reports_inconsistency_when_compensation_fails(db):
	db.fail_audit_insert = True
	discord = _Discord()
	discord.delete.side_effect = Exception("boom")

	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord)

	assert exc_info.value.status_code == 500
	assert "inconsistent" in exc_info.value.detail


@pytest.mark.asyncio
async def test_concurrent_duplicate_name_deletes_discord_role(db):
	discord = _Discord()

	# 検証のあと、保存までの間に同名のロールが作られた
	def add_duplicate(guild_id, token, payload):
		db.add_role("13", "splatoon", category_id="cat-game")
		return _created(payload)

	discord.create.side_effect = add_duplicate
	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db, discord)

	assert exc_info.value.status_code == 409
	discord.delete.assert_awaited_once()
	assert NEW_ROLE_ID not in db.roles


@pytest.mark.asyncio
async def test_assign_failure_keeps_role(db):
	discord = _Discord(add_error=Exception("boom"))

	result = await _self_create(db, discord)

	assert result["ok"] is True
	assert result["assigned"] is False
	assert NEW_ROLE_ID in db.roles
	assert db.members_of(NEW_ROLE_ID) == set()
	discord.delete.assert_not_called()


@pytest.mark.asyncio
async def test_assignment_db_failure_reverts_discord_assignment(db, monkeypatch):
	def fail(*args, **kwargs):
		raise RuntimeError("db down")

	monkeypatch.setattr(roles_api, "batch_update_user_roles", fail)
	discord = _Discord()

	result = await _self_create(db, discord)

	assert result["assigned"] is False
	assert NEW_ROLE_ID in db.roles
	discord.remove.assert_awaited_once_with(roles_api.DISCORD_GUILD_ID, "500", NEW_ROLE_ID, "token")


@pytest.mark.asyncio
async def test_rate_limit(db):
	for _ in range(ROLE_SELF_CREATE_RATE_LIMIT):
		with pytest.raises(HTTPException) as exc_info:
			await _self_create(db, payload=_payload(category_id="cat-info"))
		assert exc_info.value.status_code == 403

	with pytest.raises(HTTPException) as exc_info:
		await _self_create(db)
	assert exc_info.value.status_code == 429
