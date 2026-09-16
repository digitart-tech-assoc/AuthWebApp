"""役割: PostgreSQL接続管理 & ログユーティリティ

repository.py から分離した共通インフラ層。
全リポジトリモジュールはこのモジュールの _connect() を使用する。
"""

from __future__ import annotations

import os
import sys
from typing import Any
from urllib.parse import urlparse
from datetime import datetime
import json

import psycopg2


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres")


def _connect():
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
