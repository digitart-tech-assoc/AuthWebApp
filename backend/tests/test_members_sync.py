"""POST /roles/members/sync のギルドメンバー保存のテスト（#181）

- Discord のギルドメンバーは 1 回の全件取得で取り、ロールごとの所属メンバーは role_ids から組み立てる
- 同期対象のロールを持たないメンバー（sub垢 のみのアカウントや Bot など）も guild_members に保存する
- 所属メンバーが 0 人のロールも空リストとして sync_member_lists に渡す
- 会員種別はロール名ではなく、環境変数で設定したロール ID で判定する（#234）
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fastapi import HTTPException

from app.api.v1 import roles as roles_api

GUILD_ID = "guild-1"

DISCORD_ROLES = [
	{"role_id": "role-member", "name": "member"},
	{"role_id": "role-obog", "name": "OBOG"},
	{"role_id": "role-admin", "name": "管理者"},
	{"role_id": "role-pre", "name": "pre-member"},
	{"role_id": "role-sub", "name": "sub垢"},
]


def _member(user_id: str, role_ids: list[str]) -> dict:
	return {
		"user_id": user_id,
		"username": f"name-{user_id}",
		"display_name": f"display-{user_id}",
		"avatar": None,
		"role_ids": role_ids,
	}


GUILD_MEMBERS = [
	_member("user-member", ["role-member"]),
	_member("user-admin", ["role-member", "role-admin"]),
	_member("user-sub", ["role-sub"]),
	_member("user-bot", []),
]

EMPTY_RESULT = {
	"member_list": [],
	"sub_user_list": [],
	"admin_list": [],
	"pre_member_list": [],
	"obog_list": [],
}


ROLE_ID_ENV = {
	"MEMBER_ROLE_IDS": "role-member",
	"OBOG_ROLE_IDS": "role-obog",
	"ADMIN_ROLE_IDS": "role-admin",
	"PRE_MEMBER_ROLE_ID": "role-pre",
	"SUB_USER_ROLE_IDS": "role-sub",
}


@pytest.fixture(autouse=True)
def membership_role_env(monkeypatch):
	"""会員種別のロール ID を環境変数に設定する。"""
	for name, value in ROLE_ID_ENV.items():
		monkeypatch.setenv(name, value)


@pytest.fixture
def run_sync():
	"""Discord の応答をモックして sync_members_from_discord を実行し、呼び出されたモックを返す。"""

	async def _run():
		with patch.object(roles_api, "_get_token", return_value="token"), \
			patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
			patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
			patch.object(roles_api, "fetch_all_guild_members", new_callable=AsyncMock, return_value=GUILD_MEMBERS) as mock_fetch_all, \
			patch.object(roles_api, "save_guild_members") as mock_save, \
			patch.object(roles_api, "sync_member_lists", return_value=EMPTY_RESULT) as mock_sync:
			result = await roles_api.sync_members_from_discord({"app_role": "admin"})
		return result, mock_fetch_all, mock_save, mock_sync

	return _run


class TestSyncMembersSavesGuildMembers:
	@pytest.mark.asyncio
	async def test_fetches_all_guild_members_once(self, run_sync):
		result, mock_fetch_all, _, _ = await run_sync()

		assert result["ok"] is True
		mock_fetch_all.assert_awaited_once()

	@pytest.mark.asyncio
	async def test_returns_lists_of_all_membership_types(self, run_sync):
		# obog_list を含む全種別の同期結果を返す（#183）
		result, _, _, _ = await run_sync()

		assert result == {"ok": True, "guild_id": GUILD_ID, **EMPTY_RESULT}

	@pytest.mark.asyncio
	async def test_saves_members_without_synced_roles(self, run_sync):
		_, _, mock_save, _ = await run_sync()

		mock_save.assert_called_once()
		saved_ids = {m["user_id"] for m in mock_save.call_args.args[0]}
		assert saved_ids == {"user-member", "user-admin", "user-sub", "user-bot"}

	@pytest.mark.asyncio
	async def test_builds_members_per_role_from_role_ids(self, run_sync):
		_, _, _, mock_sync = await run_sync()

		members_data = mock_sync.call_args.args[4]
		ids_by_role = {role_id: {m["user_id"] for m in members} for role_id, members in members_data.items()}
		assert ids_by_role["role-member"] == {"user-member", "user-admin"}
		assert ids_by_role["role-admin"] == {"user-admin"}

	@pytest.mark.asyncio
	async def test_passes_empty_list_for_roles_without_members(self, run_sync):
		_, _, _, mock_sync = await run_sync()

		members_data = mock_sync.call_args.args[4]
		assert members_data["role-obog"] == []
		assert members_data["role-pre"] == []


def test_match_role_ids_by_membership_type():
	roles = [*DISCORD_ROLES, {"role_id": "role-game", "name": "Minecraft"}]

	matched = roles_api._match_role_ids(roles)

	assert matched == {
		"member_role_ids": ["role-member"],
		"obog_role_ids": ["role-obog"],
		"admin_role_ids": ["role-admin"],
		"pre_member_role_id": "role-pre",
		"sub_user_role_ids": ["role-sub"],
	}


def test_match_role_ids_accepts_multiple_ids(monkeypatch):
	monkeypatch.setenv("MEMBER_ROLE_IDS", "role-member, role-member-2")
	roles = [*DISCORD_ROLES, {"role_id": "role-member-2", "name": "会員2"}]

	matched = roles_api._match_role_ids(roles)

	assert matched["member_role_ids"] == ["role-member", "role-member-2"]


def test_match_role_ids_ignores_renamed_roles():
	# 正規ロールをリネームしても、ID が同じなら判定は変わらない
	roles = [{**role, "name": f"renamed-{i}"} for i, role in enumerate(DISCORD_ROLES)]

	matched = roles_api._match_role_ids(roles)

	assert matched["admin_role_ids"] == ["role-admin"]
	assert matched["member_role_ids"] == ["role-member"]
	assert matched["pre_member_role_id"] == "role-pre"


def test_match_role_ids_ignores_roles_with_reserved_names():
	# 予約名と同じ名前のロールがあっても、設定した ID でなければ会員種別として扱わない
	roles = [
		*DISCORD_ROLES,
		{"role_id": "role-fake-admin", "name": "管理者"},
		{"role_id": "role-fake-member", "name": "member"},
	]

	matched = roles_api._match_role_ids(roles)

	assert matched["admin_role_ids"] == ["role-admin"]
	assert matched["member_role_ids"] == ["role-member"]


def test_match_role_ids_leaves_optional_types_empty_when_unset(monkeypatch):
	monkeypatch.delenv("OBOG_ROLE_IDS")
	monkeypatch.setenv("SUB_USER_ROLE_IDS", "")

	matched = roles_api._match_role_ids(DISCORD_ROLES)

	assert matched["obog_role_ids"] == []
	assert matched["sub_user_role_ids"] == []


@pytest.mark.parametrize("env_var", ["ADMIN_ROLE_IDS", "MEMBER_ROLE_IDS", "PRE_MEMBER_ROLE_ID"])
def test_match_role_ids_rejects_missing_required_ids(monkeypatch, env_var):
	monkeypatch.delenv(env_var)

	with pytest.raises(HTTPException) as exc_info:
		roles_api._match_role_ids(DISCORD_ROLES)

	assert exc_info.value.status_code == 400
	assert env_var in exc_info.value.detail


def test_match_role_ids_rejects_ids_not_found_in_discord():
	# 設定したロールが Discord で削除されている場合、その種別の行を消さないよう同期を止める
	roles = [role for role in DISCORD_ROLES if role["role_id"] != "role-obog"]

	with pytest.raises(HTTPException) as exc_info:
		roles_api._match_role_ids(roles)

	assert exc_info.value.status_code == 400
	assert "OBOG_ROLE_IDS" in exc_info.value.detail


@pytest.mark.asyncio
async def test_sync_aborts_before_saving_when_required_ids_are_missing(monkeypatch):
	monkeypatch.delenv("ADMIN_ROLE_IDS")
	with patch.object(roles_api, "_get_token", return_value="token"), \
		patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=DISCORD_ROLES), \
		patch.object(roles_api, "fetch_all_guild_members", new_callable=AsyncMock, return_value=GUILD_MEMBERS), \
		patch.object(roles_api, "save_guild_members") as mock_save, \
		patch.object(roles_api, "sync_member_lists") as mock_sync:
		with pytest.raises(HTTPException) as exc_info:
			await roles_api.sync_members_from_discord({"app_role": "admin"})

	assert exc_info.value.status_code == 400
	mock_save.assert_not_called()
	mock_sync.assert_not_called()
