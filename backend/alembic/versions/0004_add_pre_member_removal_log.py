"""add pre_member_removal_log table

Revision ID: 0004_add_pre_member_removal_log
Revises: 0003_add_student_registration
Create Date: 2026-03-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_pre_member_removal_log'
down_revision = '0003_add_student_registration'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'pre_member_removal_log',
        sa.Column('id', sa.Text, primary_key=True, server_default=sa.text("gen_random_uuid()::TEXT")),
        sa.Column('discord_id', sa.Text, nullable=False),
        sa.Column('source_flow', sa.Text, nullable=True),
        sa.Column('expired_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('removed_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
        sa.Column('reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()')),
    )


def downgrade():
    op.drop_table('pre_member_removal_log')
