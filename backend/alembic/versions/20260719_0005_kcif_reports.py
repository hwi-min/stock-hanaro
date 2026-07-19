"""create kcif reports

Revision ID: 20260719_0005
Revises: 20260719_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0005"
down_revision = "20260719_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kcif_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_no", sa.String(30), nullable=False, unique=True),
        sa.Column("report_date", sa.Date(), nullable=False), sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.String(120)), sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("source_url", sa.Text(), nullable=False), sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_kcif_reports_report_no", "kcif_reports", ["report_no"], unique=True)
    op.create_index("ix_kcif_reports_report_date", "kcif_reports", ["report_date"])
    op.create_index("ix_kcif_reports_file_hash", "kcif_reports", ["file_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("kcif_reports")
