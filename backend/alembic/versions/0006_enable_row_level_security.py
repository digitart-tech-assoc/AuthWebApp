"""enable row level security on public tables

Revision ID: 0006_enable_row_level_security
Revises: 0005_add_member_survey_responses
Create Date: 2026-10-20

Supabase では anon キーがブラウザに公開され、PostgREST 経由で public スキーマに
アクセスできるため、全テーブルで RLS を有効にする。
Backend は所有者ロールで接続するため RLS の影響を受けない（FORCE は付けない）。
本番・開発 DB では手動で有効化済みのため、この migration はその状態をリポジトリに記録する。
"""

from __future__ import annotations

from alembic import op


revision = "0006_enable_row_level_security"
down_revision = "0005_add_member_survey_responses"
branch_labels = None
depends_on = None


# Alembic 以外で作成されたテーブルも含むため、存在しない環境でも失敗しないよう IF EXISTS を付ける
RLS_TABLES = (
    "alembic_version",
    "audit_logs",
    "events",
    "guild_members",
    "join_requests",
    "member_survey_responses",
    "otp_codes",
    "otp_records",
    "paid_invitations",
    "pre_member_removal_log",
    "role_assignments",
    "role_categories",
    "role_changes",
    "role_manifests",
    "role_member_assignments",
    "student_profiles",
    "user_memberships",
    "users",
)


def upgrade() -> None:
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE IF EXISTS {table} ENABLE ROW LEVEL SECURITY")

    # ビューは既定で所有者権限で動き RLS を素通りするため、呼び出し元の権限で評価させる
    op.execute("ALTER VIEW IF EXISTS v_users_with_app_role SET (security_invoker = on)")


def downgrade() -> None:
    # この migration 以前から DB 上では RLS が有効だったため、無効化すると元の状態より公開範囲が広がる。
    # 安全側に倒し、downgrade では何もしない。
    pass
