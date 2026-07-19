"""create pipeline runs

Revision ID: 20260717_0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20260717_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    status = sa.Enum("queued", "running", "succeeded", "partial", "failed", "skipped", name="pipeline_status")
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_name", sa.String(100), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("github_run_id", sa.String(100)),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("input_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skip_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text()),
        sa.Column("retry_of", sa.String(36)),
        sa.Column("code_version", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("job_name", "idempotency_key", name="uq_pipeline_job_key"),
    )
    op.create_index("ix_pipeline_runs_job_name", "pipeline_runs", ["job_name"])
    op.create_index("ix_pipeline_runs_business_date", "pipeline_runs", ["business_date"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_runs_business_date", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_job_name", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
