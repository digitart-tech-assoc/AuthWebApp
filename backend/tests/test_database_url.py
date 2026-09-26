"""DATABASE_URL 変換ユーティリティ（app.db.database_url）のテスト"""
from __future__ import annotations

import pytest

from app.db.database_url import with_psycopg2_driver


@pytest.mark.parametrize(
	("url", "expected"),
	[
		(
			"postgresql://user:pass@localhost:5432/db",
			"postgresql+psycopg2://user:pass@localhost:5432/db",
		),
		(
			"postgres://user:pass@localhost:5432/db",
			"postgresql+psycopg2://user:pass@localhost:5432/db",
		),
		(
			"postgresql://user:p%40ss@host.example.com:6543/db?sslmode=require",
			"postgresql+psycopg2://user:p%40ss@host.example.com:6543/db?sslmode=require",
		),
	],
)
def test_driverless_postgres_url_gets_psycopg2_driver(url: str, expected: str) -> None:
	assert with_psycopg2_driver(url) == expected


@pytest.mark.parametrize(
	"url",
	[
		"postgresql+psycopg2://user:pass@localhost:5432/db",
		"postgresql+psycopg://user:pass@localhost:5432/db",
		"sqlite:///local.db",
	],
)
def test_url_with_explicit_driver_or_other_dialect_is_unchanged(url: str) -> None:
	assert with_psycopg2_driver(url) == url


def test_resolves_to_psycopg2_dialect() -> None:
	"""SQLAlchemy のバージョンに関わらず psycopg2 dialect が選ばれることを確認する。"""
	from sqlalchemy.engine import make_url

	url = make_url(with_psycopg2_driver("postgresql://user:pass@localhost:5432/db"))
	assert url.get_dialect().driver == "psycopg2"
