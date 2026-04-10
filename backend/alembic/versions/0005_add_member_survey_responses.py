"""add member_survey_responses table

Revision ID: 0005_add_member_survey_responses
Revises: 0004_add_pre_member_removal_log
Create Date: 2026-04-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_add_member_survey_responses"
down_revision = "0004_add_pre_member_removal_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "member_survey_responses",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("profile_id", sa.Text(), nullable=True),
        sa.Column("student_number", sa.Text(), nullable=False),
        sa.Column("join_request_id", sa.Text(), nullable=True),

        sa.Column("digitart_channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("digitart_channels_other", sa.Text(), nullable=True),

        sa.Column("circle_search_channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("circle_search_other", sa.Text(), nullable=True),

        sa.Column("discord_invite_source", sa.Text(), nullable=True),
        sa.Column("discord_invite_other", sa.Text(), nullable=True),

        sa.Column("interested_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("interested_fields_other", sa.Text(), nullable=True),

        sa.Column("motivations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("motivations_other", sa.Text(), nullable=True),

        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["profile_id"], ["student_profiles.id"], ondelete="SET NULL"),
    )

    op.create_index("idx_member_survey_student_number", "member_survey_responses", ["student_number"])
    op.create_index("idx_member_survey_created_at", "member_survey_responses", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_member_survey_created_at", table_name="member_survey_responses")
    op.drop_index("idx_member_survey_student_number", table_name="member_survey_responses")
    op.drop_table("member_survey_responses")
