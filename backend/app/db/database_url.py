"""DATABASE_URL の変換ユーティリティ。"""

from __future__ import annotations

import re

_DRIVERLESS_POSTGRES_SCHEME = re.compile(r"^postgres(?:ql)?://")


def with_psycopg2_driver(url: str) -> str:
	"""ドライバ未指定の PostgreSQL URL に psycopg2 ドライバを明示する。

	SQLAlchemy 2.1 以降は `postgresql://` の既定ドライバが psycopg (v3) になったため、
	依存している psycopg2 を使うよう `postgresql+psycopg2://` に書き換える。
	ドライバが明示済みの URL や PostgreSQL 以外の URL はそのまま返す。
	"""
	return _DRIVERLESS_POSTGRES_SCHEME.sub("postgresql+psycopg2://", url, count=1)
