"""add KRX stock masters

Revision ID: 20260719_0010
Revises: 20260719_0009
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0010"
down_revision = "20260719_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_masters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(12), nullable=False, unique=True),
        sa.Column("isin", sa.String(20)), sa.Column("name", sa.String(150), nullable=False),
        sa.Column("market", sa.String(10), nullable=False),
        sa.Column("product_type", sa.String(10), nullable=False, server_default="ST"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    for column in ("symbol", "isin", "name", "market", "active"):
        op.create_index(f"ix_stock_masters_{column}", "stock_masters", [column], unique=column == "symbol")


def downgrade() -> None:
    op.drop_table("stock_masters")
