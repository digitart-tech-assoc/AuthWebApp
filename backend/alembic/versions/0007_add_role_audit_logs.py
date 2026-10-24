"""add role_audit_logs table

Revision ID: 0007_add_role_audit_logs
Revises: 0006_enable_row_level_security
Create Date: 2026-10-23

ロール定義・割り当ての変更履歴（DB 側・Discord 側）を残すテーブル。
保存するのは ID（Supabase UUID / Discord ID）とロール定義だけで、メンバーの名前などの個人情報は保存しない。
"""

from __future__ import annotations

from alembic import op


revision = "0007_add_role_audit_logs"
down_revision = "0006_enable_row_level_security"
branch_labels = None
depends_on = None


CREATE_ROLE_AUDIT_LOGS = """
CREATE TABLE role_audit_logs (
    id               TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    occurred_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id       TEXT NOT NULL,
    operation        TEXT NOT NULL,
    system           TEXT NOT NULL CHECK (system IN ('db', 'discord')),
    target_type      TEXT NOT NULL,
    target_id        TEXT NOT NULL,
    action           TEXT NOT NULL,
    before           JSONB,
    after            JSONB,
    actor_sub        TEXT,
    actor_discord_id TEXT
)
"""


def upgrade() -> None:
    op.execute(CREATE_ROLE_AUDIT_LOGS)
    op.execute(
        "CREATE INDEX idx_role_audit_logs_target ON role_audit_logs (target_type, target_id, occurred_at DESC)"
    )
    op.execute("CREATE INDEX idx_role_audit_logs_occurred_at ON role_audit_logs (occurred_at DESC)")
    # 0006 は実行時点の全テーブルが対象で、後から作るテーブルには効かないため明示する
    op.execute("ALTER TABLE role_audit_logs ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS role_audit_logs")
