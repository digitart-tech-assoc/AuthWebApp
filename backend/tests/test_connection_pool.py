"""クライアント側コネクションプール（app.db.connection）のテスト

実DBには接続せず、psycopg2 接続を模したモックを SQLAlchemy QueuePool に渡して挙動を検証する。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import psycopg2
import pytest

from app.db import connection


def _make_raw_conn() -> MagicMock:
	conn = MagicMock()
	conn.closed = 0
	conn.autocommit = False
	conn.isolation_level = psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
	return conn


@pytest.fixture
def creator():
	"""プールをリセットし、生接続の生成関数をモックに差し替える。"""
	connection.dispose_pool()
	mock_creator = MagicMock(side_effect=lambda: _make_raw_conn())
	with patch.object(connection, "_create_raw_connection", mock_creator), \
		patch.object(connection, "DB_POOL_SIZE", 2), \
		patch.object(connection, "DB_POOL_MAX_OVERFLOW", 0), \
		patch.object(connection, "DB_POOL_TIMEOUT", 0.1):
		yield mock_creator
	connection.dispose_pool()


class TestConnectionReuse:
	def test_sequential_connects_reuse_same_raw_connection(self, creator):
		with connection._connect() as conn1:
			raw1 = conn1._conn
		with connection._connect() as conn2:
			raw2 = conn2._conn

		assert raw1 is raw2
		assert creator.call_count == 1

	def test_close_returns_connection_to_pool(self, creator):
		conn = connection._connect()
		raw = conn._conn
		conn.close()
		conn.close()  # 二重 close しても例外にならない

		with connection._connect() as conn2:
			assert conn2._conn is raw
		assert creator.call_count == 1

	def test_pool_exhausted_raises_timeout(self, creator):
		held = [connection._connect(), connection._connect()]
		try:
			with pytest.raises(Exception, match="timed out"):
				connection._connect()
		finally:
			for c in held:
				c.close()


class TestTransactionHandling:
	def test_with_block_commits_on_success(self, creator):
		with connection._connect() as conn:
			raw = conn._conn
		raw.commit.assert_called_once()

	def test_with_block_rolls_back_on_exception(self, creator):
		# 借用時 ping と返却時リセットでも rollback が呼ばれるため、呼び出し順で __exit__ の rollback を検証する
		calls: list[str] = []
		with pytest.raises(RuntimeError):
			with connection._connect() as conn:
				raw = conn._conn
				raw.rollback.reset_mock()  # 借用時 ping 後の rollback を除外
				raw.rollback.side_effect = lambda: calls.append("rollback")
				close = conn.close
				conn.close = lambda: (calls.append("close"), close())
				raise RuntimeError("boom")
		raw.commit.assert_not_called()
		# プールへ返却（close）する前に rollback されていること
		assert calls[:2] == ["rollback", "close"]

	def test_close_without_commit_rolls_back_on_return(self, creator):
		conn = connection._connect()
		raw = conn._conn
		raw.rollback.reset_mock()
		conn.close()
		raw.rollback.assert_called()

	def test_attributes_are_delegated_to_raw_connection(self, creator):
		with connection._connect() as conn:
			cur = conn.cursor()
			assert cur is conn._conn.cursor.return_value

	def test_session_attributes_are_reset_on_return(self, creator):
		conn = connection._connect()
		raw = conn._conn
		raw.autocommit = True
		raw.isolation_level = psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE
		conn.close()

		assert raw.autocommit is False
		raw.set_isolation_level.assert_called_with(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)


class TestStaleConnectionHandling:
	def test_broken_connection_on_checkout_is_replaced(self, creator):
		with connection._connect() as conn:
			stale = conn._conn
		# プール内でアイドル中に切断された状態を再現
		stale.cursor.return_value.__enter__.return_value.execute.side_effect = psycopg2.OperationalError("server closed")

		with connection._connect() as conn:
			assert conn._conn is not stale
		assert creator.call_count == 2
		stale.close.assert_called()

	def test_connection_closed_during_use_is_discarded(self, creator):
		conn = connection._connect()
		broken = conn._conn
		broken.rollback.reset_mock()  # 借用時 ping 後の rollback を除外
		broken.closed = 2
		conn.close()

		with connection._connect() as conn2:
			assert conn2._conn is not broken
		broken.rollback.assert_not_called()
		broken.close.assert_called()


class TestDisposePool:
	def test_dispose_closes_pooled_connections(self, creator):
		with connection._connect() as conn:
			raw = conn._conn
		connection.dispose_pool()

		raw.close.assert_called()
		assert connection._pool is None

	def test_dispose_without_pool_is_noop(self):
		connection.dispose_pool()
		connection.dispose_pool()
		assert connection._pool is None


class TestNoNestedCheckout:
	"""接続を保持したまま別の接続を借用しないこと（プール枯渇による待ち合いの防止）を検証する。"""

	@pytest.fixture
	def single_slot_pool(self, creator):
		with patch.object(connection, "DB_POOL_SIZE", 1):
			yield creator

	def _cursor(self, creator):
		# プールは生接続を1本だけ作るため、以降の借用はすべて同じカーソルモックを使う
		with connection._connect() as conn:
			return conn._conn.cursor.return_value.__enter__.return_value

	def test_upsert_existing_user_with_single_connection(self, single_slot_pool):
		from app.db.user_repository import upsert_user

		cur = self._cursor(single_slot_pool)
		cur.fetchone.side_effect = [(1, "user-1", "discord-1"), ("sub_user",)]

		user = upsert_user("user-1", "discord-1")

		assert user == {"id": 1, "user_id": "user-1", "discord_id": "discord-1", "app_role": "member"}
		assert single_slot_pool.call_count == 1

	def test_upsert_new_user_with_single_connection(self, single_slot_pool):
		from app.db.user_repository import upsert_user

		cur = self._cursor(single_slot_pool)
		cur.fetchone.side_effect = [None, None, (2, "user-2", "discord-2"), ("admin",)]

		user = upsert_user("user-2", "discord-2")

		assert user == {"id": 2, "user_id": "user-2", "discord_id": "discord-2", "app_role": "admin"}
		assert single_slot_pool.call_count == 1
