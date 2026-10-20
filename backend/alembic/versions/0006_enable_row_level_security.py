"""enable row level security on public tables

Revision ID: 0006_enable_row_level_security
Revises: 0005_add_member_survey_responses
Create Date: 2026-10-20

Supabase では anon キーがブラウザに公開され、PostgREST 経由で public スキーマに
アクセスできるため、全テーブルで RLS を有効にする。
Backend は所有者ロールで接続するため RLS の影響を受けない（FORCE は付けない）。
本番 DB では手動で有効化済みのため、この migration はその状態をリポジトリに記録し、他の環境も同じ設定に揃える。
"""

from __future__ import annotations

from alembic import op


revision = "0006_enable_row_level_security"
down_revision = "0005_add_member_survey_responses"
branch_labels = None
depends_on = None


# 環境によってテーブル構成が異なる（Alembic 以外で作成されたテーブルや旧テーブルがある）ため、
# 列挙せず public スキーマの全テーブルを対象にする
ENABLE_RLS_ON_PUBLIC_TABLES = """
DO $$
DECLARE t text;
BEGIN
    FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
    END LOOP;
END $$
"""


def upgrade() -> None:
    op.execute(ENABLE_RLS_ON_PUBLIC_TABLES)

    # ビューは既定で所有者権限で動き RLS を素通りするため、呼び出し元の権限で評価させる
    op.execute("ALTER VIEW IF EXISTS v_users_with_app_role SET (security_invoker = on)")


def downgrade() -> None:
    # 本番 DB ではこの migration 以前から RLS が有効だったため、無効化すると元の状態より公開範囲が広がる。
    # 安全側に倒し、downgrade では何もしない。
    pass
