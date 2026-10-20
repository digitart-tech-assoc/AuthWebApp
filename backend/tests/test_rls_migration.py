"""RLS 有効化とビューの security_invoker がリポジトリに記録されていることのテスト"""

import importlib.util
import re
import sys
import types
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
VERSIONS_DIR = BACKEND_DIR / "alembic" / "versions"


def _load_rls_migration(monkeypatch, op):
	# backend/alembic ディレクトリが alembic パッケージを隠すため、op を差し込んだダミーモジュールで読み込む
	monkeypatch.setitem(sys.modules, "alembic", types.SimpleNamespace(op=op))
	path = VERSIONS_DIR / "0006_enable_row_level_security.py"
	spec = importlib.util.spec_from_file_location("rls_migration", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class _RecordingOp:
	def __init__(self):
		self.statements = []

	def execute(self, sql):
		self.statements.append(sql)


def test_upgrade_enables_rls_on_all_public_tables_and_view(monkeypatch):
	recorder = _RecordingOp()
	migration = _load_rls_migration(monkeypatch, recorder)

	migration.upgrade()

	assert migration.ENABLE_RLS_ON_PUBLIC_TABLES in recorder.statements
	assert "FROM pg_tables WHERE schemaname = 'public'" in migration.ENABLE_RLS_ON_PUBLIC_TABLES
	assert "ENABLE ROW LEVEL SECURITY" in migration.ENABLE_RLS_ON_PUBLIC_TABLES
	assert "FORCE" not in migration.ENABLE_RLS_ON_PUBLIC_TABLES
	assert "ALTER VIEW IF EXISTS v_users_with_app_role SET (security_invoker = on)" in recorder.statements


def test_downgrade_does_not_disable_rls(monkeypatch):
	recorder = _RecordingOp()
	migration = _load_rls_migration(monkeypatch, recorder)

	migration.downgrade()

	assert not any("DISABLE ROW LEVEL SECURITY" in sql for sql in recorder.statements)


def test_view_definitions_use_security_invoker():
	view_definitions = [
		BACKEND_DIR / "alembic" / "migration_view_users_with_app_role.sql",
		REPO_ROOT / "setup_migration.py",
		BACKEND_DIR / "app" / "db" / "schema.py",
	]
	for path in view_definitions:
		text = path.read_text()
		assert re.search(r"CREATE OR REPLACE VIEW v_users_with_app_role\s+WITH \(security_invoker = on\) AS", text), path
