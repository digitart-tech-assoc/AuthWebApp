"""push のロール割り当て差分をメンバー単位の PATCH にまとめるテスト（#169）

- 1 メンバーの複数ロールの追加・削除が、set_member_roles 1 回にまとまる
- 差分の対象外のロール（DB 未登録・managed・Bot より上）は現在の状態のまま残る
- 404 / 403 はスキップし、その他の失敗は errors に記録して次のメンバーを処理する
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1 import roles as roles_api
from app.services.discord_client import DiscordAPIError

GUILD_ID = "guild-1"

# Discord 上のロール（並び替え後の最新状態）
LATEST_ROLES = [
	{"role_id": GUILD_ID, "position": 0, "managed": False},
	{"role_id": "role-a", "position": 1, "managed": False},
	{"role_id": "role-b", "position": 2, "managed": False},
	{"role_id": "role-c", "position": 3, "managed": False},
	{"role_id": "role-booster", "position": 4, "managed": True},
	{"role_id": "role-bot", "position": 5, "managed": True, "is_our_bot": True},
	{"role_id": "role-above-bot", "position": 6, "managed": False},
]
ACTUAL_BY_ID = {role["role_id"]: role for role in LATEST_ROLES}


@pytest.fixture
def run_diffs():
	"""DB の割り当てと Discord のメンバー状態を与えて _apply_role_assignment_diffs を実行する。"""

	async def _run(desired_assignments: dict, current_members: list[dict], set_side_effect=None, deleted_role_ids=None):
		with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
			patch.object(roles_api, "fetch_role_assignments", return_value=desired_assignments), \
			patch.object(roles_api, "fetch_all_guild_members", new_callable=AsyncMock, return_value=current_members), \
			patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=LATEST_ROLES), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock, side_effect=set_side_effect) as mock_set:
			result = await roles_api._apply_role_assignment_diffs(
				ACTUAL_BY_ID, set(), deleted_role_ids or set(), "token"
			)
		return result, mock_set

	return _run


def _member(user_id: str, role_ids: list[str]) -> dict:
	return {"user_id": user_id, "role_ids": role_ids}


def _patched_roles(mock_set: AsyncMock) -> dict[str, set[str]]:
	"""set_member_roles の呼び出しを {user_id: 設定したロール集合} にする。"""
	return {c.args[1]: set(c.args[2]) for c in mock_set.await_args_list}


class TestApplyRoleAssignmentDiffs:
	@pytest.mark.asyncio
	async def test_multiple_role_diffs_are_merged_into_one_patch_per_member(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-b": ["user-1"], "role-c": []}
		members = [_member("user-1", ["role-c", "role-unknown", "role-booster"])]

		(adds, removes, errors), mock_set = await run_diffs(desired, members)

		assert mock_set.await_count == 1
		# role-a / role-b を追加、role-c を削除。DB 未登録の role-unknown と managed の role-booster は残る
		assert _patched_roles(mock_set) == {"user-1": {"role-a", "role-b", "role-unknown", "role-booster"}}
		assert (adds, removes, errors) == (2, 1, [])

	@pytest.mark.asyncio
	async def test_members_without_diff_are_not_patched(self, run_diffs):
		desired = {"role-a": ["user-1", "user-2"]}
		members = [_member("user-1", ["role-a"]), _member("user-2", [])]

		(adds, removes, errors), mock_set = await run_diffs(desired, members)

		assert _patched_roles(mock_set) == {"user-2": {"role-a"}}
		assert (adds, removes, errors) == (1, 0, [])

	@pytest.mark.asyncio
	async def test_roles_not_in_assignments_are_removed(self, run_diffs):
		desired = {"role-a": ["user-1"]}
		members = [_member("user-1", ["role-a", "role-b"])]

		(adds, removes, errors), mock_set = await run_diffs(desired, members)

		assert _patched_roles(mock_set) == {"user-1": {"role-a"}}
		assert (adds, removes, errors) == (0, 1, [])

	@pytest.mark.asyncio
	async def test_unmanageable_and_deleted_roles_are_excluded_from_diff(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-booster": ["user-1"], "role-above-bot": ["user-1"], "role-b": ["user-1"]}
		members = [_member("user-1", [])]

		(adds, removes, errors), mock_set = await run_diffs(desired, members, deleted_role_ids={"role-b"})

		# managed / Bot より上 / 削除済みのロールは付与しない
		assert _patched_roles(mock_set) == {"user-1": {"role-a"}}
		assert (adds, removes, errors) == (1, 0, [])

	@pytest.mark.asyncio
	async def test_users_not_in_guild_are_skipped(self, run_diffs):
		desired = {"role-a": ["user-1", "user-left"]}
		members = [_member("user-1", [])]

		(adds, removes, errors), mock_set = await run_diffs(desired, members)

		assert _patched_roles(mock_set) == {"user-1": {"role-a"}}
		assert (adds, removes, errors) == (1, 0, [])

	@pytest.mark.asyncio
	@pytest.mark.parametrize("status_code", [403, 404])
	async def test_forbidden_or_not_found_is_skipped_without_error(self, run_diffs, status_code):
		desired = {"role-a": ["user-1", "user-2"]}
		members = [_member("user-1", []), _member("user-2", [])]
		side_effect = [DiscordAPIError("failed", status_code), None]

		(adds, removes, errors), mock_set = await run_diffs(desired, members, set_side_effect=side_effect)

		assert mock_set.await_count == 2
		assert (adds, removes, errors) == (1, 0, [])

	@pytest.mark.asyncio
	async def test_other_failures_are_recorded_and_next_member_is_processed(self, run_diffs):
		desired = {"role-a": ["user-1", "user-2"]}
		members = [_member("user-1", []), _member("user-2", [])]
		side_effect = [DiscordAPIError("server error", 500), None]

		(adds, removes, errors), mock_set = await run_diffs(desired, members, set_side_effect=side_effect)

		assert mock_set.await_count == 2
		assert adds == 1
		assert len(errors) == 1
		assert "user-1" in errors[0]

	@pytest.mark.asyncio
	async def test_falls_back_to_initial_roles_when_refetching_roles_fails(self):
		desired = {"role-a": ["user-1"], "role-new": ["user-1"], "role-above-bot": ["user-1"]}
		members = [_member("user-1", [])]
		with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
			patch.object(roles_api, "fetch_role_assignments", return_value=desired), \
			patch.object(roles_api, "fetch_all_guild_members", new_callable=AsyncMock, return_value=members), \
			patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, side_effect=Exception("boom")), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			adds, removes, errors = await roles_api._apply_role_assignment_diffs(
				ACTUAL_BY_ID, {"role-new"}, set(), "token"
			)

		# 開始時のロール一覧で判定し、新規作成したロールも付与する。Bot より上のロールは付与しない
		assert _patched_roles(mock_set) == {"user-1": {"role-a", "role-new"}}
		assert (adds, removes, errors) == (2, 0, [])

	@pytest.mark.asyncio
	async def test_failure_to_fetch_members_is_recorded(self):
		with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
			patch.object(roles_api, "fetch_role_assignments", return_value={}), \
			patch.object(roles_api, "fetch_all_guild_members", new_callable=AsyncMock, side_effect=Exception("boom")), \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock) as mock_set:
			adds, removes, errors = await roles_api._apply_role_assignment_diffs(ACTUAL_BY_ID, set(), set(), "token")

		mock_set.assert_not_awaited()
		assert (adds, removes) == (0, 0)
		assert errors == ["Failed to apply assignment diffs: boom"]
