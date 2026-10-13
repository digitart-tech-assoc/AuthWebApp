"""POST /roles/members/sync のギルドメンバー保存のテスト（#181）

- Discord のギルドメンバーは 1 回の全件取得で取り、ロールごとの所属メンバーは role_ids から組み立てる
- 同期対象のロールを持たないメンバー（sub垢 のみのアカウントや Bot など）も guild_members に保存する
- 所属メンバーが 0 人のロールも空リストとして sync_member_lists に渡す
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

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
