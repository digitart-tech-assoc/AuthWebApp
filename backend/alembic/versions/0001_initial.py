"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	op.create_table(
		"role_categories",
		sa.Column("id", sa.Text(), primary_key=True),
		sa.Column("name", sa.Text(), nullable=False),
		sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
		sa.Column("is_collapsed", sa.Boolean(), nullable=False, server_default=sa.false()),
	)
	op.create_table(
		"role_manifests",
		sa.Column("role_id", sa.Text(), primary_key=True),
		sa.Column("name", sa.Text(), nullable=False),
		sa.Column("color", sa.Text(), nullable=False, server_default="#000000"),
		sa.Column("hoist", sa.Boolean(), nullable=False, server_default=sa.false()),
		sa.Column("mentionable", sa.Boolean(), nullable=False, server_default=sa.false()),
		sa.Column("permissions", sa.BigInteger(), nullable=False, server_default="0"),
		sa.Column("position", sa.Integer(), nullable=False),
		sa.Column("category_id", sa.Text(), nullable=True),
		sa.Column("is_managed_by_app", sa.Boolean(), nullable=False, server_default=sa.true()),
		sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
		sa.ForeignKeyConstraint(["category_id"], ["role_categories.id"], ondelete="SET NULL"),
	)


def downgrade() -> None:
	op.drop_table("role_manifests")
	op.drop_table("role_categories")
