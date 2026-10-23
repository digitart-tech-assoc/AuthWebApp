"""0007（role_audit_logs）のマイグレーションのテスト"""

import importlib.util
import sys
import types
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
MIGRATION_PATH = BACKEND_DIR / "alembic" / "versions" / "0007_add_role_audit_logs.py"


class _RecordingOp:
	def __init__(self):
		self.statements = []

	def execute(self, sql):
		self.statements.append(sql)


def _load_migration(monkeypatch, op):
	# backend/alembic ディレクトリが alembic パッケージを隠すため、op を差し込んだダミーモジュールで読み込む
	monkeypatch.setitem(sys.modules, "alembic", types.SimpleNamespace(op=op))
	spec = importlib.util.spec_from_file_location("role_audit_migration", MIGRATION_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def test_revision_follows_rls_migration(monkeypatch):
	migration = _load_migration(monkeypatch, _RecordingOp())

	assert migration.revision == "0007_add_role_audit_logs"
	assert migration.down_revision == "0006_enable_row_level_security"


def test_upgrade_creates_table_and_enables_rls(monkeypatch):
	recorder = _RecordingOp()
	migration = _load_migration(monkeypatch, recorder)

	migration.upgrade()

	assert migration.CREATE_ROLE_AUDIT_LOGS in recorder.statements
	assert "CHECK (system IN ('db', 'discord'))" in migration.CREATE_ROLE_AUDIT_LOGS
	assert "ALTER TABLE role_audit_logs ENABLE ROW LEVEL SECURITY" in recorder.statements
	assert any("idx_role_audit_logs_target" in sql for sql in recorder.statements)
	assert any("idx_role_audit_logs_occurred_at" in sql for sql in recorder.statements)


def test_downgrade_drops_table(monkeypatch):
	recorder = _RecordingOp()
	migration = _load_migration(monkeypatch, recorder)

	migration.downgrade()

	assert recorder.statements == ["DROP TABLE IF EXISTS role_audit_logs"]


def test_local_schema_defines_same_table():
	text = (BACKEND_DIR / "app" / "db" / "schema.py").read_text()

	assert "CREATE TABLE IF NOT EXISTS role_audit_logs" in text
	assert "CHECK (system IN ('db', 'discord'))" in text
