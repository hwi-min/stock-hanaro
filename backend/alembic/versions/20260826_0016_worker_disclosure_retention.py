"""allow the Worker to enforce disclosure retention

Revision ID: 20260826_0016
Revises: 20260826_0015
"""

from alembic import op


revision = "20260826_0016"
down_revision = "20260826_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("GRANT DELETE ON TABLE public.disclosures TO service_role")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("REVOKE DELETE ON TABLE public.disclosures FROM service_role")
