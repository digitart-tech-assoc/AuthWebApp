"""sync_member_lists の差分同期のテスト（#182）

- user_memberships を全件削除せず、種別ごとに Discord にいなくなった行だけを削除し、新しく現れたメンバーだけを追加する
- 既存の行の assigned_by / assigned_at は保たれる
- sub_user（sub垢）も同期する
- 対応するロールが Discord に見つからない種別は変更しない
- members/sync は sub垢 ロールを sub_user として sync_member_lists に渡し、sub_user_list を返す
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1 import roles as roles_api
from app.db import membership_repository

OLD_ASSIGNED_AT = datetime(2025, 4, 1, tzinfo=timezone.utc)


class _FakeCursor:
	"""sync_member_lists が発行する SQL だけを、メモリ上の user_memberships に対して処理する。"""

	def __init__(self, conn: "_FakeConnection"):
		self._conn = conn
		self._rows: list[tuple] = []

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def execute(self, sql: str, params: tuple = ()):
		normalized = " ".join(sql.split())
		self._conn.executed.append(normalized)
		table = self._conn.table
		if normalized.startswith("SELECT discord_id FROM user_memberships WHERE membership_type"):
			self._rows = [(d,) for (d, t) in table if t == params[0]]
		elif normalized.startswith("SELECT discord_id, membership_type, assigned_by, assigned_at, created_at"):
			self._rows = [
				(d, t, row["assigned_by"], row["assigned_at"], row["created_at"])
				for (d, t), row in table.items()
				if t == params[0]
			]
		elif normalized.startswith("DELETE FROM user_memberships WHERE membership_type = %s AND discord_id = ANY(%s)"):
			m_type, ids = params
			for discord_id in ids:
				table.pop((discord_id, m_type), None)
		elif normalized.startswith("INSERT INTO user_memberships"):
			discord_id, m_type = params
			now = datetime.now(timezone.utc)
			table.setdefault((discord_id, m_type), {"assigned_by": None, "assigned_at": now, "created_at": now})
		else:
			raise AssertionError(f"unexpected SQL: {normalized}")

	def fetchall(self):
		return self._rows


class _FakeConnection:
	def __init__(self, table: dict[tuple[str, str], dict]):
		self.table = table
		self.executed: list[str] = []
		self.committed = False

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def cursor(self):
		return _FakeCursor(self)

	def commit(self):
		self.committed = True


def _row(assigned_by: str | None = None) -> dict:
	return {"assigned_by": assigned_by, "assigned_at": OLD_ASSIGNED_AT, "created_at": OLD_ASSIGNED_AT}


def _members(*user_ids: str) -> list[dict]:
	return [{"user_id": user_id} for user_id in user_ids]


@pytest.fixture
def run_sync(monkeypatch):
	"""既存の user_memberships を与えて sync_member_lists を実行し、(結果, 実行後のテーブル, 接続) を返す。"""

	def _run(table: dict, *, member_role_ids=("role-member",), obog_role_ids=("role-obog",),
			admin_role_ids=("role-admin",), pre_member_role_id="role-pre", sub_user_role_ids=("role-sub",),
			members: dict | None = None):
		conn = _FakeConnection(table)
		monkeypatch.setattr(membership_repository, "_connect", lambda: conn)
		result = membership_repository.sync_member_lists(
			list(member_role_ids),
			list(obog_role_ids),
			list(admin_role_ids),
			pre_member_role_id,
			members or {},
			list(sub_user_role_ids),
		)
		return result, table, conn

	return _run


def _all_role_members(**overrides) -> dict:
	members = {"role-member": [], "role-obog": [], "role-admin": [], "role-pre": [], "role-sub": []}
	members.update(overrides)
	return members


class TestSyncMemberListsDiff:
	def test_does_not_delete_all_rows(self, run_sync):
		_, _, conn = run_sync({}, members=_all_role_members())

		assert "DELETE FROM user_memberships" not in conn.executed
		assert all("WHERE membership_type" in sql for sql in conn.executed if sql.startswith("DELETE"))
		assert conn.committed is True

	def test_removes_only_members_no_longer_in_discord(self, run_sync):
		table = {("user-stay", "member"): _row(), ("user-left", "member"): _row()}

		_, table, _ = run_sync(table, members=_all_role_members(**{"role-member": _members("user-stay")}))

		assert set(table) == {("user-stay", "member")}

	def test_adds_new_members(self, run_sync):
		table = {("user-stay", "member"): _row()}

		_, table, _ = run_sync(table, members=_all_role_members(**{"role-member": _members("user-stay", "user-new")}))

		assert set(table) == {("user-stay", "member"), ("user-new", "member")}

	def test_keeps_assigned_by_and_assigned_at_of_existing_rows(self, run_sync):
		table = {("user-pre", "pre_member"): _row(assigned_by="P")}

		_, table, _ = run_sync(table, members=_all_role_members(**{"role-pre": _members("user-pre")}))

		assert table[("user-pre", "pre_member")]["assigned_by"] == "P"
		assert table[("user-pre", "pre_member")]["assigned_at"] == OLD_ASSIGNED_AT

	def test_syncs_sub_user(self, run_sync):
		table = {("user-sub-left", "sub_user"): _row()}

		result, table, _ = run_sync(table, members=_all_role_members(**{"role-sub": _members("user-sub")}))

		assert set(table) == {("user-sub", "sub_user")}
		assert [row["discord_id"] for row in result["sub_user_list"]] == ["user-sub"]

	def test_leaves_types_without_matched_role_unchanged(self, run_sync):
		table = {("user-sub", "sub_user"): _row(assigned_by="admin"), ("user-obog", "obog"): _row()}

		_, table, _ = run_sync(
			table,
			sub_user_role_ids=(),
			obog_role_ids=(),
			members={"role-member": [], "role-admin": [], "role-pre": []},
		)

		assert ("user-sub", "sub_user") in table
		assert table[("user-sub", "sub_user")]["assigned_by"] == "admin"
		assert ("user-obog", "obog") in table

	def test_returns_all_rows_after_sync_per_type(self, run_sync):
		table = {("user-a", "member"): _row(), ("user-x", "admin"): _row()}

		result, _, _ = run_sync(table, members=_all_role_members(**{"role-member": _members("user-a", "user-b")}))

		assert {row["discord_id"] for row in result["member_list"]} == {"user-a", "user-b"}
		assert result["admin_list"] == []
		assert set(result) == {"member_list", "sub_user_list", "admin_list", "pre_member_list", "obog_list"}
		assert all(isinstance(row["assigned_at"], str) for row in result["member_list"])

	def test_aborts_when_members_data_is_missing(self, run_sync):
		with pytest.raises(ValueError):
			run_sync({}, members={"role-member": []})


class TestMembersSyncPassesSubUser:
	@pytest.mark.asyncio
	async def test_passes_sub_user_role_and_returns_sub_user_list(self):
		discord_roles = [
			{"role_id": "role-member", "name": "member"},
			{"role_id": "role-sub", "name": "sub垢"},
		]
		guild_members = [
			{"user_id": "user-sub", "username": "sub", "display_name": "sub", "avatar": None, "role_ids": ["role-sub"]},
		]
		sync_result = {
			"member_list": [],
			"sub_user_list": [{"discord_id": "user-sub"}],
			"admin_list": [],
			"pre_member_list": [],
			"obog_list": [],
		}
		with patch.object(roles_api, "_get_token", return_value="token"), \
			patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=discord_roles), \
			patch.object(roles_api, "fetch_all_guild_members", new_callable=AsyncMock, return_value=guild_members), \
			patch.object(roles_api, "save_guild_members"), \
			patch.object(roles_api, "sync_member_lists", return_value=sync_result) as mock_sync:
			result = await roles_api.sync_members_from_discord({"app_role": "admin"})

		args = mock_sync.call_args.args
		assert args[5] == ["role-sub"]
		assert [m["user_id"] for m in args[4]["role-sub"]] == ["user-sub"]
		assert result["sub_user_list"] == [{"discord_id": "user-sub"}]
