"""add market quote taxonomy

Revision ID: 20260719_0006
Revises: 20260719_0005
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0006"
down_revision = "20260719_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("market_quotes", sa.Column("asset_type", sa.String(20), nullable=False, server_default="equity"))
    op.add_column("market_quotes", sa.Column("sector", sa.String(80)))
    op.add_column("market_quotes", sa.Column("industry", sa.String(120)))
    op.create_index("ix_market_quotes_asset_type", "market_quotes", ["asset_type"])
    op.create_index("ix_market_quotes_sector", "market_quotes", ["sector"])


def downgrade() -> None:
    op.drop_index("ix_market_quotes_sector", table_name="market_quotes")
    op.drop_index("ix_market_quotes_asset_type", table_name="market_quotes")
    op.drop_column("market_quotes", "industry")
    op.drop_column("market_quotes", "sector")
    op.drop_column("market_quotes", "asset_type")
