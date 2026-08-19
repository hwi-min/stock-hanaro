"""create research report metadata

Revision ID: 20260819_0012
Revises: 20260719_0011
"""
from alembic import op
import sqlalchemy as sa

revision = "20260819_0012"
down_revision = "20260719_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("source_report_id", sa.String(80), nullable=False, unique=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("broker", sa.String(100), nullable=False),
        sa.Column("analyst", sa.String(200)),
        sa.Column("published_on", sa.Date(), nullable=False),
        sa.Column("stock_code", sa.String(12)),
        sa.Column("stock_name", sa.String(100)),
        sa.Column("opinion", sa.String(40)),
        sa.Column("target_price", sa.Integer()),
        sa.Column("previous_target_price", sa.Integer()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("source", "source_report_id", "category", "broker", "analyst", "published_on", "stock_code", "stock_name"):
        op.create_index(f"ix_research_reports_{column}", "research_reports", [column], unique=column == "source_report_id")


def downgrade() -> None:
    op.drop_table("research_reports")

