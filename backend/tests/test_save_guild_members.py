"""ギルドメンバーの保存を一括 UPSERT にしたことのテスト（#190）

実DBには接続せず、execute_values が使う範囲だけを模したカーソルで、発行する SQL の回数と値を確認する。
"""

import ast
from unittest.mock import MagicMock

import pytest

from app.db import guild_repository

# execute_values の既定のページサイズ
PAGE_SIZE = 100


class FakeCursor:
	"""mogrify は値を repr で埋め込むだけの代替。実行した SQL を記録する。"""

	def __init__(self):
		self.connection = MagicMock(encoding="UTF8")
		self.statements: list[str] = []

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, tb):
		return None

	def mogrify(self, template, args):
		return (template.decode("utf-8") % tuple(repr(arg) for arg in args)).encode("utf-8")

	def execute(self, sql):
		self.statements.append(sql.decode("utf-8"))


@pytest.fixture
def db(monkeypatch):
	cur = FakeCursor()
	conn = MagicMock()
	conn.__enter__.return_value = conn
	conn.cursor.return_value = cur
	monkeypatch.setattr(guild_repository, "_connect", lambda: conn)
	return conn, cur


def _member(user_id, **kwargs):
	row = {"user_id": user_id, "username": f"user-{user_id}", "display_name": None, "avatar": None}
	row.update(kwargs)
	return row


def _saved_rows(statement):
	"""INSERT 文の VALUES 句から行のタプルを取り出す。"""
	values = statement.split("VALUES", 1)[1].split("ON CONFLICT", 1)[0]
	return list(ast.literal_eval(f"[{values.strip()}]"))


def test_saves_all_members_in_one_statement(db):
	conn, cur = db

	guild_repository.save_guild_members([_member(str(i)) for i in range(PAGE_SIZE)])

	assert len(cur.statements) == 1
	assert len(_saved_rows(cur.statements[0])) == PAGE_SIZE
	conn.commit.assert_called_once()


def test_statement_count_grows_by_page_not_by_member(db):
	_, cur = db

	guild_repository.save_guild_members([_member(str(i)) for i in range(PAGE_SIZE + 1)])

	assert len(cur.statements) == 2
	assert sum(len(_saved_rows(statement)) for statement in cur.statements) == PAGE_SIZE + 1


def test_upsert_updates_existing_rows(db):
	_, cur = db

	guild_repository.save_guild_members([_member("1")])

	statement = cur.statements[0]
	assert "ON CONFLICT (user_id) DO UPDATE SET" in statement
	for assignment in (
		"username = EXCLUDED.username",
		"display_name = EXCLUDED.display_name",
		"avatar = EXCLUDED.avatar",
		"updated_at = now()",
	):
		assert assignment in statement


def test_saves_only_guild_member_columns_and_defaults_optional_ones_to_none(db):
	_, cur = db

	guild_repository.save_guild_members([
		{"user_id": "1", "username": "name-1", "display_name": "shown-1", "avatar": "hash-1", "role_ids": ["10"]},
		{"user_id": "2", "username": "name-2"},
	])

	assert _saved_rows(cur.statements[0]) == [
		("1", "name-1", "shown-1", "hash-1"),
		("2", "name-2", None, None),
	]


def test_duplicate_user_id_keeps_last_row(db):
	# 同じ文に同じ主キーがあると Postgres が ON CONFLICT DO UPDATE を拒否するため、1行にまとめてから送る
	_, cur = db

	guild_repository.save_guild_members([
		_member("1", username="old"),
		_member("2"),
		_member("1", username="new"),
	])

	assert _saved_rows(cur.statements[0]) == [("1", "new", None, None), ("2", "user-2", None, None)]


def test_empty_members_issue_no_statement(db):
	_, cur = db

	guild_repository.save_guild_members([])

	assert cur.statements == []
