"""add join_requests and otp_codes tables for OTP authentication

Revision ID: 0002_join_otp
Revises: 0001_initial
Create Date: 2026-03-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_join_otp"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"join_requests",
		sa.Column("id", sa.Text(), primary_key=True),  # UUID
		sa.Column("email", sa.Text(), nullable=False, unique=True),
		sa.Column("name", sa.Text(), nullable=False),
		sa.Column("form_type", sa.Text(), nullable=False),  # prospective-student, contact
		sa.Column("status", sa.Text(), nullable=False, server_default="pending"),  # pending, verified, completed, failed
		sa.Column("metadata", sa.JSON(), nullable=True),  # form_type-specific fields
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
	)
	op.create_index("idx_join_requests_email", "join_requests", ["email"])
	op.create_index("idx_join_requests_status", "join_requests", ["status"])

	op.create_table(
		"otp_codes",
		sa.Column("id", sa.Text(), primary_key=True),  # UUID
		sa.Column("join_request_id", sa.Text(), nullable=False),
		sa.Column("code_hash", sa.Text(), nullable=False),  # bcrypt hash
		sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
		sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
		sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.ForeignKeyConstraint(["join_request_id"], ["join_requests.id"], ondelete="CASCADE"),
	)
	op.create_index("idx_otp_codes_join_request_id", "otp_codes", ["join_request_id"])
	op.create_index("idx_otp_codes_expires_at", "otp_codes", ["expires_at"])


def downgrade() -> None:
	op.drop_table("otp_codes")
	op.drop_table("join_requests")
