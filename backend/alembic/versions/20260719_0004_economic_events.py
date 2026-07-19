"""create economic events

Revision ID: 20260719_0004
Revises: 20260719_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0004"
down_revision = "20260719_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "economic_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(30), nullable=False), sa.Column("source_event_id", sa.String(180), nullable=False),
        sa.Column("country", sa.String(2), nullable=False), sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.Text(), nullable=False), sa.Column("scheduled_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_at_kst", sa.DateTime(timezone=True), nullable=False),
        sa.Column("importance", sa.String(10), nullable=False), sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_event_id", name="uq_economic_event_source_id"),
    )
    for column in ("source", "country", "scheduled_at_utc", "importance"):
        op.create_index(f"ix_economic_events_{column}", "economic_events", [column])


def downgrade() -> None:
    op.drop_table("economic_events")
