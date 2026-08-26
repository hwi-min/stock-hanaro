"""grant the Cloudflare Worker service role least-privilege Data API access

Revision ID: 20260826_0014
Revises: 20260826_0013
"""

from alembic import op


revision = "20260826_0014"
down_revision = "20260826_0013"
branch_labels = None
depends_on = None


READ_TABLES = (
    "market_quotes", "news_articles", "issue_summaries", "economic_events",
    "disclosures", "kcif_reports", "research_reports", "stock_masters",
    "api_cache", "kis_tokens",
)


def upgrade() -> None:
    for table in READ_TABLES:
        op.execute(f'GRANT SELECT ON TABLE public."{table}" TO service_role')
    op.execute("GRANT INSERT, UPDATE ON TABLE public.api_cache TO service_role")
    op.execute("GRANT INSERT, UPDATE ON TABLE public.kis_tokens TO service_role")


def downgrade() -> None:
    op.execute("REVOKE INSERT, UPDATE ON TABLE public.kis_tokens FROM service_role")
    op.execute("REVOKE INSERT, UPDATE ON TABLE public.api_cache FROM service_role")
    for table in READ_TABLES:
        op.execute(f'REVOKE SELECT ON TABLE public."{table}" FROM service_role')
