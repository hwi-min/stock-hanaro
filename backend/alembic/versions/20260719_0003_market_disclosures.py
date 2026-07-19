"""create market quotes and disclosures

Revision ID: 20260719_0003
Revises: 20260719_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0003"
down_revision = "20260719_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_quotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(30), nullable=False), sa.Column("market", sa.String(20), nullable=False),
        sa.Column("exchange", sa.String(20)), sa.Column("symbol", sa.String(30), nullable=False),
        sa.Column("name", sa.String(150)), sa.Column("currency", sa.String(10)),
        sa.Column("price", sa.Numeric(24, 6), nullable=False), sa.Column("change", sa.Numeric(24, 6)),
        sa.Column("change_pct", sa.Numeric(12, 6)), sa.Column("volume", sa.Numeric(28, 2)),
        sa.Column("market_cap", sa.Numeric(28, 2)), sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "market", "symbol", name="uq_market_quote_identity"),
    )
    op.create_index("ix_market_quotes_market", "market_quotes", ["market"])
    op.create_index("ix_market_quotes_symbol", "market_quotes", ["symbol"])
    op.create_table(
        "disclosures",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("receipt_no", sa.String(30), nullable=False, unique=True),
        sa.Column("corp_code", sa.String(8), nullable=False), sa.Column("corp_name", sa.String(150), nullable=False),
        sa.Column("stock_code", sa.String(6)), sa.Column("title", sa.Text(), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False), sa.Column("report_type", sa.String(10)),
        sa.Column("submitter", sa.String(150)), sa.Column("remarks", sa.String(20)),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for name, column in (("receipt_no", "receipt_no"), ("corp_code", "corp_code"), ("stock_code", "stock_code"), ("receipt_date", "receipt_date")):
        op.create_index(f"ix_disclosures_{name}", "disclosures", [column], unique=name == "receipt_no")


def downgrade() -> None:
    op.drop_table("disclosures")
    op.drop_table("market_quotes")
