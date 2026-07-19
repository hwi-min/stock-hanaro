"""add ai summaries

Revision ID: 20260719_0009
Revises: 20260719_0008
"""
from alembic import op
import sqlalchemy as sa

revision = "20260719_0009"
down_revision = "20260719_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "issue_summaries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("issue_key", sa.String(80), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False), sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False), sa.Column("sentiment", sa.String(10), nullable=False),
        sa.Column("article_ids_json", sa.Text(), nullable=False), sa.Column("model", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(30), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_issue_summaries_issue_key", "issue_summaries", ["issue_key"], unique=True)
    with op.batch_alter_table("kcif_reports") as batch:
        batch.add_column(sa.Column("ai_summary", sa.Text()))
        batch.add_column(sa.Column("ai_topic", sa.String(50)))
        batch.add_column(sa.Column("ai_model", sa.String(80)))
        batch.add_column(sa.Column("ai_summarized_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    with op.batch_alter_table("kcif_reports") as batch:
        batch.drop_column("ai_summarized_at")
        batch.drop_column("ai_model")
        batch.drop_column("ai_topic")
        batch.drop_column("ai_summary")
    op.drop_table("issue_summaries")
