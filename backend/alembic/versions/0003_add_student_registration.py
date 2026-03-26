"""add student_profiles and otp_records tables

Revision ID: 0003_add_student_registration
Revises: 0002_join_otp
Create Date: 2026-03-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_add_student_registration"
down_revision = "0002_join_otp"
branch_labels = None
depends_on = None


def upgrade() -> None:
	# student_profiles table: 学生プロフィール保存
	op.create_table(
		"student_profiles",
		sa.Column("id", sa.Text(), nullable=False),
		sa.Column("discord_id", sa.Text(), nullable=False),
		sa.Column("student_number", sa.Text(), nullable=False),
		sa.Column("name", sa.Text(), nullable=False),
		sa.Column("furigana", sa.Text(), nullable=False),
		sa.Column("department", sa.Text(), nullable=False),
		sa.Column("gender", sa.Text(), nullable=True),
		sa.Column("phone", sa.Text(), nullable=False),
		sa.Column("email_aoyama", sa.Text(), nullable=False, server_default=""),
		sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
		sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("otp_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
		sa.Column("otp_verified_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("profile_submitted_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("discord_id", name="uq_student_profiles_discord_id"),
	)
	op.create_index("idx_student_profiles_student_number", "student_profiles", ["student_number"])
	op.create_index("idx_student_profiles_created_at", "student_profiles", ["created_at"])

	# otp_records table: OTP認証記録
	op.create_table(
		"otp_records",
		sa.Column("id", sa.Text(), nullable=False),
		sa.Column("discord_id", sa.Text(), nullable=False),
		sa.Column("email_aoyama", sa.Text(), nullable=False),
		sa.Column("code", sa.Text(), nullable=False),
		sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
		sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
		sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_index("idx_otp_records_discord_id", "otp_records", ["discord_id"])
	op.create_index("idx_otp_records_expires_at", "otp_records", ["expires_at"])


def downgrade() -> None:
	op.drop_index("idx_otp_records_expires_at", table_name="otp_records")
	op.drop_index("idx_otp_records_discord_id", table_name="otp_records")
	op.drop_table("otp_records")

	op.drop_index("idx_student_profiles_created_at", table_name="student_profiles")
	op.drop_index("idx_student_profiles_student_number", table_name="student_profiles")
	op.drop_table("student_profiles")
