"""create KIS token cache

Revision ID: 20260719_0007
Revises: 20260719_0006
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0007"
down_revision = "20260719_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kis_tokens",
        sa.Column("environment", sa.String(10), primary_key=True),
        sa.Column("access_token", sa.String(2000), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("kis_tokens")
