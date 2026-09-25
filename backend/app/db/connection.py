"""役割: PostgreSQL接続管理 & ログユーティリティ

repository.py から分離した共通インフラ層。
全リポジトリモジュールはこのモジュールの _connect() を使用する。
_connect() はクライアント側コネクションプールから接続を借用する。
"""

from __future__ import annotations

import os
import sys
from typing import Any
from urllib.parse import urlparse
from datetime import datetime
import json
import threading

import psycopg2
from sqlalchemy import event
from sqlalchemy import exc as sa_exc
from sqlalchemy.pool import QueuePool


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")

# クライアント側コネクションプール設定
# Supabase Pooler (Supavisor) との二重プーリングになるため、サイズは小さめに保つ。
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_POOL_MAX_OVERFLOW = int(os.getenv("DB_POOL_MAX_OVERFLOW", "5"))
DB_POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))

_pool: QueuePool | None = None
_pool_lock = threading.Lock()


def _create_raw_connection():
    parsed = urlparse(DATABASE_URL)
    connect_kwargs: dict = {"connect_timeout": 5}
    # Use SSL when connecting to Supabase-hosted DBs / pooler
    hostname = (parsed.hostname or "").lower()
    if "supabase.co" in hostname or "pooler.supabase.com" in hostname or "supabase" in hostname:
        connect_kwargs["sslmode"] = "require"
    try:
        conn = psycopg2.connect(DATABASE_URL, **connect_kwargs)
        # Explicitly set isolation_level to ensure transaction handling works
        # isolation_level=None causes autocommit, which can cause issues with pooler
        # Using READ_COMMITTED (1) ensures proper transaction behavior
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        conn.autocommit = False
        return conn
    except Exception as e:
        host = parsed.hostname or "<unknown>"
        port = parsed.port or "<unknown>"
        user = parsed.username or "<unknown>"
        print(f"ERROR: DB connection failed to host={host} port={port} user={user}: {e}", file=sys.stderr)
        raise


def _ping_on_checkout(dbapi_connection, connection_record, connection_proxy) -> None:
    """借用時のヘルスチェック。

    Supabase Pooler 側のアイドル切断などで壊れた接続を検出した場合は DisconnectionError を送出し、
    プールに破棄と新規接続での再試行を行わせる。
    """
    try:
        with dbapi_connection.cursor() as cur:
            cur.execute("SELECT 1")
        # ping で開始されたトランザクションを閉じ、借用側には未開始状態で渡す
        dbapi_connection.rollback()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
        raise sa_exc.DisconnectionError() from e


def _reset_on_checkin(dbapi_connection, connection_record) -> None:
    """返却時に接続属性を初期値へ戻し、前の借用者の設定が次の借用者へ漏れないようにする。"""
    if dbapi_connection is None or dbapi_connection.closed:
        return
    if dbapi_connection.autocommit:
        dbapi_connection.autocommit = False
    if dbapi_connection.isolation_level != psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED:
        dbapi_connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)


def _get_pool() -> QueuePool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                pool = QueuePool(
                    _create_raw_connection,
                    pool_size=DB_POOL_SIZE,
                    max_overflow=DB_POOL_MAX_OVERFLOW,
                    timeout=DB_POOL_TIMEOUT,
                    recycle=DB_POOL_RECYCLE,
                    # 返却時に rollback し、未完了トランザクションを次の借用者へ持ち越さない
                    reset_on_return="rollback",
                )
                event.listen(pool, "checkout", _ping_on_checkout)
                event.listen(pool, "checkin", _reset_on_checkin)
                _pool = pool
    return _pool


def dispose_pool() -> None:
    """プール内の接続をすべて閉じる（アプリ終了時に呼び出す）。"""
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.dispose()
            _pool = None


class _PooledConnection:
    """プールから借用した psycopg2 接続のラッパー。

    既存の呼び出し側との互換性を保つ:
    - `with _connect() as conn:` は psycopg2 と同様に正常終了で commit、例外で rollback し、その後プールへ返却する。
    - `conn = _connect(); ...; conn.close()` の close() はプールへの返却となる。
    - それ以外の属性（cursor / commit / rollback 等）は psycopg2 接続へ委譲する。
    """

    def __init__(self, fairy) -> None:
        self._fairy = fairy
        self._conn = fairy.dbapi_connection

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)

    def __enter__(self) -> "_PooledConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if not self._conn.closed:
                if exc_type is None:
                    self._conn.commit()
                else:
                    self._conn.rollback()
        finally:
            self.close()

    def close(self) -> None:
        if self._fairy is None:
            return
        fairy, self._fairy = self._fairy, None
        if self._conn.closed:
            # 使用中に切断された接続はプールへ戻さず破棄する
            fairy.invalidate()
        else:
            fairy.close()


def _connect() -> _PooledConnection:
    return _PooledConnection(_get_pool().connect())


def _should_log_to_stdout() -> bool:
	"""Return True when the DATABASE_URL appears to target Supabase (so container logs should record requests)."""
	try:
		parsed = urlparse(DATABASE_URL)
		host = (parsed.hostname or "").lower()
		return "supabase" in host or "pooler.supabase.com" in host
	except Exception:
		return False


def _log_db_access(access_point: str, payload: dict | None = None) -> None:
	"""Print a concise log line to stdout containing timestamp, access point, payload and a short preview.

	Example format (single line):
	[DB_LOG] 2026-04-06T12:00:00+00:00 access=create_join_request payload={...} preview="..."
	"""
	if not _should_log_to_stdout():
		return
	try:
		ts = datetime.now().astimezone().isoformat()
		payload_json = json.dumps(payload or {}, ensure_ascii=False)
		preview = (payload_json[:200] + "...") if len(payload_json) > 200 else payload_json
		# Use stdout so docker logs capture it
		print(f"[DB_LOG] {ts} access={access_point} payload={payload_json} preview={preview}")
	except Exception:
		# Never raise from logging
		pass
