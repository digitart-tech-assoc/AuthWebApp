"""ヘルスチェックエンドポイント（/health, /health/db）のテスト（#90）

実DBには接続せず、疎通確認関数やプールの生接続をモックに差し替えて検証する。
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import psycopg2
import pytest
from fastapi.testclient import TestClient

from app import main
from app.db import connection


@pytest.fixture
def client():
	# lifespan（DB 初期化・プール破棄）は走らせない
	return TestClient(main.app)


def test_health_returns_ok_without_db(client, monkeypatch):
	monkeypatch.setattr(main, "ping_database", MagicMock(side_effect=AssertionError("must not touch DB")))

	response = client.get("/health")

	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


def test_health_db_returns_200_when_connected(client, monkeypatch):
	ping_thread_ids = []
	monkeypatch.setattr(main, "ping_database", lambda: ping_thread_ids.append(threading.get_ident()))

	response = client.get("/health/db")

	assert response.status_code == 200
	assert response.json() == {"status": "ok", "database": "connected"}
	assert ping_thread_ids


def test_health_db_returns_503_without_leaking_error_detail(client, monkeypatch):
	def fail():
		raise psycopg2.OperationalError("could not connect to server: host=secret-host")

	monkeypatch.setattr(main, "ping_database", fail)

	response = client.get("/health/db")

	assert response.status_code == 503
	assert response.json() == {"status": "error", "database": "disconnected", "detail": "Connection error"}
	assert "secret-host" not in response.text


def test_health_db_returns_503_on_timeout(client, monkeypatch):
	monkeypatch.setattr(main, "HEALTH_DB_TIMEOUT_SECONDS", 0.05)
	monkeypatch.setattr(main, "ping_database", lambda: time.sleep(0.5))

	response = client.get("/health/db")

	assert response.status_code == 503
	assert response.json()["database"] == "disconnected"


class TestPingDatabase:
	@pytest.fixture
	def raw_conn(self):
		"""プールをリセットし、生接続をモックに差し替える。"""
		connection.dispose_pool()
		conn = MagicMock()
		conn.closed = 0
		conn.autocommit = False
		conn.isolation_level = psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
		with patch.object(connection, "_create_raw_connection", MagicMock(return_value=conn)):
			yield conn
		connection.dispose_pool()

	def test_executes_select_1(self, raw_conn):
		connection.ping_database()

		cursor = raw_conn.cursor.return_value.__enter__.return_value
		cursor.execute.assert_any_call("SELECT 1")
		raw_conn.commit.assert_called()

	def test_raises_when_query_fails(self, raw_conn):
		raw_conn.cursor.return_value.__enter__.return_value.fetchone.side_effect = psycopg2.OperationalError("down")

		with pytest.raises(psycopg2.OperationalError):
			connection.ping_database()
