"""add shared API response cache

Revision ID: 20260826_0013
Revises: 20260819_0012
"""
from alembic import op
import sqlalchemy as sa

revision = "20260826_0013"
down_revision = "20260819_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_cache",
        sa.Column("cache_key", sa.String(160), primary_key=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_api_cache_expires_at", "api_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_table("api_cache")
