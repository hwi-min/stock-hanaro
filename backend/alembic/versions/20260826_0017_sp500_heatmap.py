"""add S&P 500 heatmap master and daily snapshots

Revision ID: 20260826_0017
Revises: 20260826_0016
"""

import sqlalchemy as sa
from alembic import op


revision = "20260826_0017"
down_revision = "20260826_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sp500_constituents",
        sa.Column("symbol", sa.String(20), primary_key=True),
        sa.Column("kis_symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("sector", sa.String(80), nullable=False),
        sa.Column("industry", sa.String(120), nullable=False),
        sa.Column("index_weight", sa.Numeric(14, 8), nullable=False),
        sa.Column("source_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sp500_constituents_sector", "sp500_constituents", ["sector"])
    op.create_index("ix_sp500_constituents_active", "sp500_constituents", ["active"])
    op.create_table(
        "sp500_daily_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("symbol", sa.String(20), sa.ForeignKey("sp500_constituents.symbol"), nullable=False),
        sa.Column("close", sa.Numeric(24, 6), nullable=False),
        sa.Column("previous_close", sa.Numeric(24, 6), nullable=False),
        sa.Column("change_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("volume", sa.Numeric(28, 2)),
        sa.Column("average_volume_20d", sa.Numeric(28, 2)),
        sa.Column("dollar_volume", sa.Numeric(30, 2)),
        sa.Column("relative_volume", sa.Numeric(14, 6)),
        sa.Column("index_weight", sa.Numeric(14, 8), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("trading_date", "symbol", name="uq_sp500_snapshot_date_symbol"),
    )
    op.create_index("ix_sp500_daily_snapshots_trading_date", "sp500_daily_snapshots", ["trading_date"])
    op.create_index("ix_sp500_daily_snapshots_symbol", "sp500_daily_snapshots", ["symbol"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("GRANT SELECT ON TABLE public.sp500_constituents, public.sp500_daily_snapshots TO service_role")


def downgrade() -> None:
    op.drop_index("ix_sp500_daily_snapshots_symbol", table_name="sp500_daily_snapshots")
    op.drop_index("ix_sp500_daily_snapshots_trading_date", table_name="sp500_daily_snapshots")
    op.drop_table("sp500_daily_snapshots")
    op.drop_index("ix_sp500_constituents_active", table_name="sp500_constituents")
    op.drop_index("ix_sp500_constituents_sector", table_name="sp500_constituents")
    op.drop_table("sp500_constituents")
