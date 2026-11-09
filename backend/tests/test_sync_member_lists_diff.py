"""sync_member_lists のテスト（#182・#251）

- admin は、user_memberships を全件削除せず、Discord にいなくなった行だけを削除し、新しく現れたメンバーだけを追加する
- 既存の admin の行の assigned_by / assigned_at は保たれる
- member / sub_user / obog / pre_member は書き込まず、Discord との差分だけを返す（#251）
- 対応するロールが Discord に見つからない種別は、書き込みも差分の計算もしない
- members/sync は sub垢 ロールを sub_user として sync_member_lists に渡し、sub_user_list と diff を返す
- ギルドメンバーが 0 件で返った場合は同期を中止する
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import roles as roles_api
from app.core.config import MembershipType
from app.db import membership_repository
from app.db.membership_assignment_repository import SAVE_MANAGED_TYPES

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


DIFF_ONLY_TYPES = ("member", "sub_user", "obog", "pre_member")


class TestSyncMemberListsAdmin:
	"""admin は Discord から差分同期する（Discord を正とする）"""

	def test_does_not_delete_all_rows(self, run_sync):
		_, _, conn = run_sync({}, members=_all_role_members())

		assert "DELETE FROM user_memberships" not in conn.executed
		assert all("WHERE membership_type" in sql for sql in conn.executed if sql.startswith("DELETE"))
		assert conn.committed is True

	def test_removes_only_admins_no_longer_in_discord(self, run_sync):
		table = {("user-stay", "admin"): _row(), ("user-left", "admin"): _row()}

		_, table, _ = run_sync(table, members=_all_role_members(**{"role-admin": _members("user-stay")}))

		assert set(table) == {("user-stay", "admin")}

	def test_adds_new_admins(self, run_sync):
		table = {("user-stay", "admin"): _row()}

		_, table, _ = run_sync(table, members=_all_role_members(**{"role-admin": _members("user-stay", "user-new")}))

		assert set(table) == {("user-stay", "admin"), ("user-new", "admin")}

	def test_keeps_assigned_by_and_assigned_at_of_existing_rows(self, run_sync):
		table = {("user-admin", "admin"): _row(assigned_by="P")}

		_, table, _ = run_sync(table, members=_all_role_members(**{"role-admin": _members("user-admin")}))

		assert table[("user-admin", "admin")]["assigned_by"] == "P"
		assert table[("user-admin", "admin")]["assigned_at"] == OLD_ASSIGNED_AT

	def test_admin_is_not_in_diff(self, run_sync):
		result, _, _ = run_sync({}, members=_all_role_members(**{"role-admin": _members("user-admin")}))

		assert "admin" not in result["diff"]


class TestSyncMemberListsDoesNotWriteSaveManagedTypes:
	"""member / sub_user / obog / pre_member は書き込まず、差分だけを返す（#251）"""

	@pytest.mark.parametrize(("role_id", "m_type"), [
		("role-member", "member"), ("role-sub", "sub_user"), ("role-obog", "obog"), ("role-pre", "pre_member"),
	])
	def test_does_not_add_or_remove_rows(self, run_sync, role_id, m_type):
		table = {("user-row-only", m_type): _row(assigned_by="admin")}

		result, table, conn = run_sync(table, members=_all_role_members(**{role_id: _members("user-role-only")}))

		assert set(table) == {("user-row-only", m_type)}
		assert table[("user-row-only", m_type)]["assigned_by"] == "admin"
		assert not [sql for sql in conn.executed if sql.startswith(("INSERT", "DELETE"))]
		assert result["diff"][m_type] == {"discord_only": ["user-role-only"], "db_only": ["user-row-only"]}

	def test_diff_is_empty_when_rows_match_discord(self, run_sync):
		table = {("user-a", "member"): _row(), ("user-pre", "pre_member"): _row()}

		result, _, _ = run_sync(table, members=_all_role_members(**{
			"role-member": _members("user-a"), "role-pre": _members("user-pre"),
		}))

		assert result["diff"] == {m_type: {"discord_only": [], "db_only": []} for m_type in DIFF_ONLY_TYPES}

	def test_diff_ids_are_sorted(self, run_sync):
		result, _, _ = run_sync({}, members=_all_role_members(**{"role-member": _members("user-c", "user-a", "user-b")}))

		assert result["diff"]["member"]["discord_only"] == ["user-a", "user-b", "user-c"]

	def test_sub_account_with_member_role_is_shown_in_member_diff(self, run_sync):
		# sub垢 と member の両方のロールを Discord で持つ人は、member の行を作らず、差分として示す
		# （#187 の member からの除外は、sync で書き込まなくなったため不要）
		table = {("user-sub", "sub_user"): _row()}
		members = _all_role_members(**{"role-member": _members("user-sub"), "role-sub": _members("user-sub")})

		result, table, _ = run_sync(table, members=members)

		assert set(table) == {("user-sub", "sub_user")}
		assert result["diff"]["member"] == {"discord_only": ["user-sub"], "db_only": []}
		assert result["diff"]["sub_user"] == {"discord_only": [], "db_only": []}

	def test_types_without_matched_role_are_unchanged_and_diff_is_none(self, run_sync):
		table = {("user-sub", "sub_user"): _row(assigned_by="admin"), ("user-obog", "obog"): _row()}

		result, table, _ = run_sync(
			table,
			sub_user_role_ids=(),
			obog_role_ids=(),
			members={"role-member": [], "role-admin": [], "role-pre": []},
		)

		assert set(table) == {("user-sub", "sub_user"), ("user-obog", "obog")}
		assert result["diff"]["sub_user"] is None
		assert result["diff"]["obog"] is None


class TestSyncMemberListsResult:
	def test_returns_all_rows_per_type_and_diff(self, run_sync):
		table = {("user-a", "member"): _row(), ("user-x", "admin"): _row()}

		result, _, _ = run_sync(table, members=_all_role_members(**{"role-member": _members("user-a", "user-b")}))

		assert {row["discord_id"] for row in result["member_list"]} == {"user-a"}
		assert result["admin_list"] == []
		assert set(result) == {"member_list", "sub_user_list", "admin_list", "pre_member_list", "obog_list", "diff"}
		assert set(result["diff"]) == set(DIFF_ONLY_TYPES)
		assert all(isinstance(row["assigned_at"], str) for row in result["member_list"])

	def test_every_type_is_either_written_or_diffed(self, run_sync):
		# 全種別が、書き込む（Discord を正とする）か差分だけを返す（SAVE_MANAGED_TYPES）かの、ちょうど一方で扱われる
		members = _all_role_members(**{role_id: _members(f"user-{role_id}") for role_id in (
			"role-member", "role-sub", "role-obog", "role-admin", "role-pre",
		)})

		result, table, _ = run_sync({}, members=members)

		written_types = {m_type for _, m_type in table}
		assert set(SAVE_MANAGED_TYPES) <= set(MembershipType.ALL)
		assert set(result["diff"]) == set(SAVE_MANAGED_TYPES)
		assert written_types == set(MembershipType.ALL) - set(SAVE_MANAGED_TYPES)

	def test_aborts_when_members_data_is_missing(self, run_sync):
		with pytest.raises(ValueError):
			run_sync({}, members={"role-member": []})


def _configure_membership_roles(monkeypatch) -> list[dict]:
	"""会員種別のロール ID を環境変数に設定し、それらを含む Discord のロール一覧を返す（#234）。"""
	monkeypatch.setenv("MEMBER_ROLE_IDS", "role-member")
	monkeypatch.setenv("SUB_USER_ROLE_IDS", "role-sub")
	monkeypatch.setenv("ADMIN_ROLE_IDS", "role-admin")
	monkeypatch.setenv("PRE_MEMBER_ROLE_ID", "role-pre")
	monkeypatch.delenv("OBOG_ROLE_IDS", raising=False)
	return [
		{"role_id": "role-member", "name": "member"},
		{"role_id": "role-sub", "name": "sub垢"},
		{"role_id": "role-admin", "name": "管理者"},
		{"role_id": "role-pre", "name": "pre-member"},
	]


class TestMembersSyncPassesSubUser:
	@pytest.mark.asyncio
	async def test_passes_sub_user_role_and_returns_sub_user_list(self, monkeypatch):
		discord_roles = _configure_membership_roles(monkeypatch)
		guild_members = [
			{"user_id": "user-sub", "username": "sub", "display_name": "sub", "avatar": None, "role_ids": ["role-sub"]},
		]
		sync_result = {
			"member_list": [],
			"sub_user_list": [{"discord_id": "user-sub"}],
			"admin_list": [],
			"pre_member_list": [],
			"obog_list": [],
			"diff": {"member": {"discord_only": [], "db_only": []}},
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
		assert result["diff"] == {"member": {"discord_only": [], "db_only": []}}


class TestMembersSyncAbortsOnEmptyGuild:
	@pytest.mark.asyncio
	async def test_aborts_without_saving_when_guild_members_are_empty(self, monkeypatch):
		discord_roles = _configure_membership_roles(monkeypatch)
		with patch.object(roles_api, "_get_token", return_value="token"), \
			patch.object(roles_api, "fetch_guild_roles", new_callable=AsyncMock, return_value=discord_roles), \
			patch.object(roles_api, "fetch_all_guild_members", new_callable=AsyncMock, return_value=[]), \
			patch.object(roles_api, "save_guild_members") as mock_save, \
			patch.object(roles_api, "sync_member_lists") as mock_sync:
			with pytest.raises(HTTPException) as exc_info:
				await roles_api.sync_members_from_discord({"app_role": "admin"})

		assert exc_info.value.status_code == 502
		mock_save.assert_not_called()
		mock_sync.assert_not_called()
