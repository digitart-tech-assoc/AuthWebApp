"""push のロール割り当て差分をメンバー単位にまとめて反映するテスト（#169）

- 差分が 1 件だけのメンバーは、ほかのロールに触れない PUT / DELETE で反映する
- 差分が 2 件以上のメンバーは、メンバーの現在のロールを取り直してから set_member_roles（PATCH）1 回で反映する
- 反映の直前にメンバーの DB の割り当てを読み直し、push 開始後に変わった割り当てを元に反映する
- push 開始時のメンバー情報より後に付与・解除されたロールを、PATCH で巻き戻さない
- 差分の対象外のロール（DB 未登録・managed・Bot より上）は現在の状態のまま残る
- 404 はスキップする。403 とその他の失敗は errors に記録して次のメンバーを処理する（403 の記録には Discord ID を含めない）
- 再試行しても 429 のままなら、残りのメンバーへは送らずに打ち切り、errors に記録する（Discord ID を含めない）
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
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


def _member(user_id: str, role_ids: list[str]) -> dict:
	return {"user_id": user_id, "role_ids": role_ids}


def _http_error(status_code: int) -> httpx.HTTPStatusError:
	request = httpx.Request("PUT", "https://discord.com/api/v10/guilds/guild-1/members/user/roles/role")
	return httpx.HTTPStatusError("failed", request=request, response=httpx.Response(status_code, request=request))


@pytest.fixture
def run_diffs():
	"""DB の割り当てと Discord のメンバー状態を与えて _apply_role_assignment_diffs を実行する。

	latest_members を渡すと、PATCH 直前に取り直したメンバーの状態として返す（省略時は current_members と同じ）。
	latest_assignments を渡すと、反映直前に読み直す DB の割り当てとして返す（省略時は desired_assignments と同じ）。
	"""

	async def _run(
		desired_assignments: dict,
		current_members: list[dict],
		*,
		latest_members: dict[str, dict | None] | None = None,
		latest_assignments: dict | None = None,
		set_side_effect=None,
		add_side_effect=None,
		remove_side_effect=None,
		fetch_side_effect=None,
		deleted_role_ids=None,
		roles_side_effect=None,
		created_real_ids=None,
	):
		latest = {m["user_id"]: m for m in current_members}
		latest.update(latest_members or {})

		async def _fetch_member(_guild_id, user_id, _token, client=None):
			return latest.get(user_id)

		db_assignments = desired_assignments if latest_assignments is None else latest_assignments

		def _fetch_assignments_for_user(user_id):
			return {rid: [user_id] for rid, users in db_assignments.items() if user_id in users}

		with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
			patch.object(roles_api, "fetch_role_assignments", return_value=desired_assignments), \
			patch.object(roles_api, "fetch_role_assignments_for_user", side_effect=_fetch_assignments_for_user), \
			patch.object(roles_api, "fetch_all_guild_members", new_callable=AsyncMock, return_value=current_members), \
			patch.object(
				roles_api, "fetch_guild_roles", new_callable=AsyncMock,
				return_value=LATEST_ROLES, side_effect=roles_side_effect,
			), \
			patch.object(
				roles_api, "fetch_guild_member", new_callable=AsyncMock, side_effect=fetch_side_effect or _fetch_member,
			) as mock_fetch, \
			patch.object(roles_api, "set_member_roles", new_callable=AsyncMock, side_effect=set_side_effect) as mock_set, \
			patch.object(roles_api, "add_role_to_member", new_callable=AsyncMock, side_effect=add_side_effect) as mock_add, \
			patch.object(
				roles_api, "remove_role_from_member", new_callable=AsyncMock, side_effect=remove_side_effect,
			) as mock_remove:
			result = await roles_api._apply_role_assignment_diffs(
				ACTUAL_BY_ID, created_real_ids or set(), deleted_role_ids or set(), "token"
			)
		return SimpleNamespace(result=result, fetch=mock_fetch, set=mock_set, add=mock_add, remove=mock_remove)

	return _run


def _patched_roles(mock_set: AsyncMock) -> dict[str, set[str]]:
	"""set_member_roles の呼び出しを {user_id: 設定したロール集合} にする。"""
	return {c.args[1]: set(c.args[2]) for c in mock_set.await_args_list}


def _single_calls(mock: AsyncMock) -> list[tuple[str, str]]:
	"""add_role_to_member / remove_role_from_member の呼び出しを [(user_id, role_id)] にする。"""
	return [(c.args[1], c.args[2]) for c in mock.await_args_list]


class TestApplyRoleAssignmentDiffs:
	@pytest.mark.asyncio
	async def test_multiple_role_diffs_are_merged_into_one_patch_per_member(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-b": ["user-1"], "role-c": []}
		members = [_member("user-1", ["role-c", "role-unknown", "role-booster"])]

		run = await run_diffs(desired, members)

		assert run.fetch.await_count == 1
		assert run.set.await_count == 1
		# role-a / role-b を追加、role-c を削除。DB 未登録の role-unknown と managed の role-booster は残る
		assert _patched_roles(run.set) == {"user-1": {"role-a", "role-b", "role-unknown", "role-booster"}}
		run.add.assert_not_awaited()
		run.remove.assert_not_awaited()
		assert run.result == (2, 1, [])

	@pytest.mark.asyncio
	async def test_single_add_uses_put_without_refetch(self, run_diffs):
		desired = {"role-a": ["user-1", "user-2"]}
		members = [_member("user-1", ["role-a"]), _member("user-2", [])]

		run = await run_diffs(desired, members)

		assert _single_calls(run.add) == [("user-2", "role-a")]
		run.fetch.assert_not_awaited()
		run.set.assert_not_awaited()
		assert run.result == (1, 0, [])

	@pytest.mark.asyncio
	async def test_single_remove_uses_delete_without_refetch(self, run_diffs):
		desired = {"role-a": ["user-1"]}
		members = [_member("user-1", ["role-a", "role-b"])]

		run = await run_diffs(desired, members)

		assert _single_calls(run.remove) == [("user-1", "role-b")]
		run.fetch.assert_not_awaited()
		run.set.assert_not_awaited()
		assert run.result == (0, 1, [])

	@pytest.mark.asyncio
	async def test_patch_is_based_on_latest_member_roles(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-b": ["user-1"]}
		members = [_member("user-1", [])]
		# push 開始後に role-a と role-booster が付与された
		latest = {"user-1": _member("user-1", ["role-a", "role-booster"])}

		run = await run_diffs(desired, members, latest_members=latest)

		# 開始時の情報で上書きせず、取り直したロールを残したうえで role-b だけを追加する
		assert _patched_roles(run.set) == {"user-1": {"role-a", "role-b", "role-booster"}}
		assert run.result == (1, 0, [])

	@pytest.mark.asyncio
	async def test_member_already_up_to_date_after_refetch_is_not_patched(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-b": ["user-1"]}
		members = [_member("user-1", [])]
		latest = {"user-1": _member("user-1", ["role-a", "role-b"])}

		run = await run_diffs(desired, members, latest_members=latest)

		run.set.assert_not_awaited()
		assert run.result == (0, 0, [])

	@pytest.mark.asyncio
	async def test_member_who_left_before_refetch_is_skipped(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-b": ["user-1"]}
		members = [_member("user-1", [])]

		run = await run_diffs(desired, members, latest_members={"user-1": None})

		run.set.assert_not_awaited()
		assert run.result == (0, 0, [])

	@pytest.mark.asyncio
	async def test_patch_keeps_role_assigned_in_db_after_push_started(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-b": ["user-1"]}
		members = [_member("user-1", [])]
		# push 開始後に、メンバーが self-batch で role-c を追加した（DB と Discord の両方に反映済み）
		latest_db = {"role-a": ["user-1"], "role-b": ["user-1"], "role-c": ["user-1"]}
		latest = {"user-1": _member("user-1", ["role-c"])}

		run = await run_diffs(desired, members, latest_members=latest, latest_assignments=latest_db)

		# 開始時の DB の割り当てを元に role-c を外さない
		assert _patched_roles(run.set) == {"user-1": {"role-a", "role-b", "role-c"}}
		assert run.result == (2, 0, [])

	@pytest.mark.asyncio
	async def test_patch_does_not_restore_role_unassigned_in_db_after_push_started(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-b": ["user-1"], "role-c": ["user-1"]}
		members = [_member("user-1", [])]
		# push 開始後に、メンバーが self-batch で role-c を外した
		latest_db = {"role-a": ["user-1"], "role-b": ["user-1"]}

		run = await run_diffs(desired, members, latest_assignments=latest_db)

		assert _patched_roles(run.set) == {"user-1": {"role-a", "role-b"}}
		assert run.result == (2, 0, [])

	@pytest.mark.asyncio
	async def test_single_diff_cancelled_in_db_after_push_started_is_not_sent(self, run_diffs):
		desired = {"role-a": ["user-1"]}
		members = [_member("user-1", ["role-b"])]
		# push 開始後に、role-a の割り当てを外し role-b を割り当てた（Discord の現在の状態と一致する）
		latest_db = {"role-b": ["user-1"]}

		run = await run_diffs(desired, members, latest_assignments=latest_db)

		run.add.assert_not_awaited()
		run.remove.assert_not_awaited()
		run.fetch.assert_not_awaited()
		run.set.assert_not_awaited()
		assert run.result == (0, 0, [])

	@pytest.mark.asyncio
	async def test_single_diff_grown_in_db_after_push_started_uses_patch(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-b": ["user-2"]}
		members = [_member("user-1", []), _member("user-2", ["role-b"])]
		# push 開始後に、user-1 に role-b も割り当てた
		latest_db = {"role-a": ["user-1"], "role-b": ["user-1", "user-2"]}

		run = await run_diffs(desired, members, latest_assignments=latest_db)

		run.add.assert_not_awaited()
		assert _patched_roles(run.set) == {"user-1": {"role-a", "role-b"}}
		assert run.result == (2, 0, [])

	@pytest.mark.asyncio
	async def test_unmanageable_and_deleted_roles_are_excluded_from_diff(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-booster": ["user-1"], "role-above-bot": ["user-1"], "role-b": ["user-1"]}
		members = [_member("user-1", [])]

		run = await run_diffs(desired, members, deleted_role_ids={"role-b"})

		# managed / Bot より上 / 削除済みのロールは付与しない
		assert _single_calls(run.add) == [("user-1", "role-a")]
		run.set.assert_not_awaited()
		assert run.result == (1, 0, [])

	@pytest.mark.asyncio
	async def test_users_not_in_guild_are_skipped(self, run_diffs):
		desired = {"role-a": ["user-1", "user-left"]}
		members = [_member("user-1", [])]

		run = await run_diffs(desired, members)

		assert _single_calls(run.add) == [("user-1", "role-a")]
		assert run.result == (1, 0, [])

	@pytest.mark.asyncio
	async def test_not_found_is_skipped_without_error(self, run_diffs):
		desired = {"role-a": ["user-1", "user-2"]}
		members = [_member("user-1", []), _member("user-2", [])]
		side_effect = [_http_error(404), None]

		run = await run_diffs(desired, members, add_side_effect=side_effect)

		assert run.add.await_count == 2
		assert run.result == (1, 0, [])

	@pytest.mark.asyncio
	@pytest.mark.parametrize("path", ["single", "patch"])
	async def test_forbidden_is_recorded_without_discord_id(self, run_diffs, path):
		members = [_member("user-1", []), _member("user-2", [])]
		if path == "single":
			desired = {"role-a": ["user-1", "user-2"]}
			run = await run_diffs(desired, members, add_side_effect=[_http_error(403), None])
			expected_adds = 1
		else:
			desired = {"role-a": ["user-1", "user-2"], "role-b": ["user-1", "user-2"]}
			run = await run_diffs(desired, members, set_side_effect=[DiscordAPIError("forbidden user-1", 403), None])
			expected_adds = 2

		adds, removes, errors = run.result
		# 403 のメンバーは反映されず、次のメンバーは処理される。失敗は errors に残る
		assert (adds, removes) == (expected_adds, 0)
		assert len(errors) == 1
		assert "HTTP 403" in errors[0]
		assert "user-1" not in errors[0]

	@pytest.mark.asyncio
	async def test_other_failures_are_recorded_and_next_member_is_processed(self, run_diffs):
		desired = {"role-a": ["user-1", "user-2"], "role-b": ["user-1", "user-2"]}
		members = [_member("user-1", []), _member("user-2", [])]
		side_effect = [DiscordAPIError("server error", 500), None]

		run = await run_diffs(desired, members, set_side_effect=side_effect)

		assert run.set.await_count == 2
		adds, _removes, errors = run.result
		assert adds == 2
		assert len(errors) == 1
		assert "user-1" in errors[0]

	@pytest.mark.asyncio
	@pytest.mark.parametrize("path", ["single_add", "single_remove", "refetch", "patch"])
	async def test_rate_limited_aborts_remaining_members(self, run_diffs, path):
		members = [_member("user-1", []), _member("user-2", []), _member("user-3", [])]
		both_roles = {"role-a": ["user-1", "user-2", "user-3"], "role-b": ["user-1", "user-2", "user-3"]}
		if path == "single_add":
			desired = {"role-a": ["user-1", "user-2", "user-3"]}
			kwargs = {"add_side_effect": [None, _http_error(429)]}
		elif path == "single_remove":
			desired = {}
			members = [_member(user_id, ["role-a"]) for user_id in ("user-1", "user-2", "user-3")]
			kwargs = {"remove_side_effect": [None, _http_error(429)]}
		elif path == "refetch":
			desired = both_roles
			kwargs = {"fetch_side_effect": [members[0], _http_error(429)]}
		else:
			desired = both_roles
			kwargs = {"set_side_effect": [None, DiscordAPIError("rate limited user-2", 429)]}

		run = await run_diffs(desired, members, **kwargs)

		# user-1 は反映し、429 を受けた user-2 で打ち切って user-3 には送らない
		sent_users = {
			c.args[1]
			for mock in (run.add, run.remove, run.fetch, run.set)
			for c in mock.await_args_list
		}
		assert sent_users == {"user-1", "user-2"}
		adds, removes, errors = run.result
		assert adds + removes in (1, 2)
		assert len(errors) == 1
		assert "HTTP 429" in errors[0]
		assert "remaining 2 members" in errors[0]
		assert "user-2" not in errors[0]

	@pytest.mark.asyncio
	async def test_falls_back_to_initial_roles_when_refetching_roles_fails(self, run_diffs):
		desired = {"role-a": ["user-1"], "role-new": ["user-1"], "role-above-bot": ["user-1"]}
		members = [_member("user-1", [])]

		run = await run_diffs(desired, members, roles_side_effect=Exception("boom"), created_real_ids={"role-new"})

		# 開始時のロール一覧で判定し、新規作成したロールも付与する。Bot より上のロールは付与しない
		assert _patched_roles(run.set) == {"user-1": {"role-a", "role-new"}}
		assert run.result == (2, 0, [])

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
