"""add disclosure taxonomy

Revision ID: 20260719_0008
Revises: 20260719_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0008"
down_revision = "20260719_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("disclosures") as batch:
        batch.add_column(sa.Column("corp_cls", sa.String(1), nullable=False, server_default="E"))
        batch.add_column(sa.Column("category", sa.String(30), nullable=False, server_default="기타공시"))
        batch.add_column(sa.Column("importance", sa.String(10), nullable=False, server_default="low"))
        batch.add_column(sa.Column("is_correction", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_index("ix_disclosures_corp_cls", ["corp_cls"])
        batch.create_index("ix_disclosures_category", ["category"])
        batch.create_index("ix_disclosures_importance", ["importance"])


def downgrade() -> None:
    with op.batch_alter_table("disclosures") as batch:
        batch.drop_index("ix_disclosures_importance")
        batch.drop_index("ix_disclosures_category")
        batch.drop_index("ix_disclosures_corp_cls")
        batch.drop_column("is_correction")
        batch.drop_column("importance")
        batch.drop_column("category")
        batch.drop_column("corp_cls")
