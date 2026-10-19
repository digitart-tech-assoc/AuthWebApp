"""push の並び替え件数（reordered）のテスト（#167）

- 並び順が変わらなければ 0 を返す（Discord への並び替えリクエスト自体は従来どおり送る）
- 一部のロールだけを動かした場合は、動かしたロールの数を返す
- ロールの作成で既存ロールの position が一律にずれても、並び順が変わらなければ数えない
- 今回作成したロールは created で数えるため、並び替えの件数に含めない
- 並び替えに失敗した場合は 0 を返す
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1 import roles as roles_api

GUILD_ID = "1000"


def _actual(*roles: tuple[str, int]) -> dict:
	"""(role_id, Discord 上の position) から actual_by_id を作る。"""
	by_id = {GUILD_ID: {"role_id": GUILD_ID, "position": 0}}
	for role_id, position in roles:
		by_id[role_id] = {"role_id": role_id, "position": position}
	return by_id


def _desired(*role_ids: str) -> list[dict]:
	"""下から上の順に並べたロール ID から、マニフェストのロール一覧を作る（position は上ほど大きい）。"""
	return [{"role_id": GUILD_ID, "position": 0}] + [
		{"role_id": role_id, "position": index} for index, role_id in enumerate(role_ids, start=1)
	]


@pytest.fixture
def run_reorder():
	async def _run(desired_roles: list[dict], actual_by_id: dict, created_real_ids: set[str] | None = None, *, fail: bool = False):
		reorder = AsyncMock(side_effect=RuntimeError("failed") if fail else None)
		with patch.object(roles_api, "DISCORD_GUILD_ID", GUILD_ID), \
			patch.object(roles_api, "reorder_guild_roles", reorder), \
			patch.object(roles_api, "_log_push_error"):
			reordered, errors = await roles_api._reorder_roles(desired_roles, actual_by_id, created_real_ids or set(), "token")
		return reordered, errors, reorder

	return _run


@pytest.mark.asyncio
async def test_unchanged_order_returns_zero(run_reorder):
	reordered, errors, reorder = await run_reorder(
		_desired("11", "12", "13"),
		_actual(("11", 1), ("12", 2), ("13", 3)),
	)

	assert reordered == 0
	assert errors == []
	# 送信内容は従来どおり全ロール分の連番
	reorder.assert_awaited_once()
	assert reorder.await_args.args[2] == [
		{"id": "11", "position": 1},
		{"id": "12", "position": 2},
		{"id": "13", "position": 3},
	]


@pytest.mark.asyncio
async def test_non_contiguous_positions_with_same_order_returns_zero(run_reorder):
	# managed ロールなど、マニフェストにないロールが間にあって position が飛んでいても、並び順が同じなら 0
	reordered, _, _ = await run_reorder(
		_desired("11", "12", "13"),
		_actual(("11", 2), ("12", 5), ("13", 6)),
	)

	assert reordered == 0


@pytest.mark.asyncio
async def test_moving_one_role_to_top_counts_one(run_reorder):
	# 11 を最下位から最上位へ移動する（ほかのロールの position の値はすべて変わるが、動かしたのは 1 件）
	reordered, _, _ = await run_reorder(
		_desired("12", "13", "14", "11"),
		_actual(("11", 1), ("12", 2), ("13", 3), ("14", 4)),
	)

	assert reordered == 1


@pytest.mark.asyncio
async def test_swapping_two_pairs_counts_two(run_reorder):
	reordered, _, _ = await run_reorder(
		_desired("12", "11", "14", "13"),
		_actual(("11", 1), ("12", 2), ("13", 3), ("14", 4)),
	)

	assert reordered == 2


@pytest.mark.asyncio
async def test_reversed_order_counts_all_but_one(run_reorder):
	reordered, _, _ = await run_reorder(
		_desired("13", "12", "11"),
		_actual(("11", 1), ("12", 2), ("13", 3)),
	)

	assert reordered == 2


@pytest.mark.asyncio
async def test_created_role_is_not_counted(run_reorder):
	# 20 を新規作成した。Discord は作成時に 20 を position 1 に置き、既存ロールを一律に 1 つ上へずらす。
	# actual_by_id の既存ロールは push 開始時の値のまま。
	desired = _desired("11", "20", "12", "13")
	actual = _actual(("11", 1), ("12", 2), ("13", 3), ("20", 1))

	reordered, _, reorder = await run_reorder(desired, actual, {"20"})

	assert reordered == 0
	# 作成したロールも並び替えのリクエストには含める
	assert {"id": "20", "position": 2} in reorder.await_args.args[2]


@pytest.mark.asyncio
async def test_same_position_is_ordered_by_role_id(run_reorder):
	# position が同じロールは ID 順に並ぶものとして比べる
	reordered, _, _ = await run_reorder(
		_desired("11", "12"),
		_actual(("11", 1), ("12", 1)),
	)

	assert reordered == 0


@pytest.mark.asyncio
async def test_reorder_failure_returns_zero(run_reorder):
	reordered, errors, _ = await run_reorder(
		_desired("12", "11"),
		_actual(("11", 1), ("12", 2)),
		fail=True,
	)

	assert reordered == 0
	assert len(errors) == 1
