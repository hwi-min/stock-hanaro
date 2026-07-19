"""add realtime worker coordination tables

Revision ID: 20260719_0011
Revises: 20260719_0010
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0011"
down_revision = "20260719_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "realtime_subscriptions",
        sa.Column("symbol", sa.String(12), primary_key=True),
        sa.Column("viewer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "realtime_worker_states",
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("configured_stock_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("accepted_subscription_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_tick_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("realtime_worker_states")
    op.drop_table("realtime_subscriptions")
