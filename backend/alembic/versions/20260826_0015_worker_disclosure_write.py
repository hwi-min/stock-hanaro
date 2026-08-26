"""allow the Worker to upsert on-demand disclosure refreshes

Revision ID: 20260826_0015
Revises: 20260826_0014
"""

from alembic import op


revision = "20260826_0015"
down_revision = "20260826_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("GRANT INSERT, UPDATE ON TABLE public.disclosures TO service_role")
    op.execute("GRANT USAGE, SELECT ON SEQUENCE public.disclosures_id_seq TO service_role")


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("REVOKE USAGE, SELECT ON SEQUENCE public.disclosures_id_seq FROM service_role")
    op.execute("REVOKE INSERT, UPDATE ON TABLE public.disclosures FROM service_role")
