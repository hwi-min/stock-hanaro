from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.collectors.news.naver_finance import NaverFinanceNewsCollector
from app.collectors.news.normalizer import canonicalize_url, normalize_article
from app.core.database import Base
from app.models.news_article import NewsArticle
from app.repositories.news import NewsRepository
from app.repositories.pipeline_runs import PipelineRunRepository


def test_canonicalize_url_removes_tracking_and_fragment():
    assert canonicalize_url("HTTPS://Example.com/a?utm_source=x&id=3#top") == "https://example.com/a?id=3"


def test_naver_finance_parser_normalizes_article():
    html = """
    <ul class="realtimeNewsList"><li>
      <dd class="articleSubject"><a title="  시장   뉴스 " href="/news/news_read.naver?article_id=123&office_id=456">기사</a></dd>
      <dd class="articleSummary">요약 문장 <span class="press">테스트경제</span><span class="wdate">2026-07-19 06:30</span></dd>
    </li></ul>
    """
    article = NaverFinanceNewsCollector().parse(html)[0]
    assert article.title == "시장 뉴스"
    assert article.source_article_id == "456:123"
    assert article.publisher == "테스트경제"
    assert article.summary == "요약 문장"


def test_news_upsert_and_pipeline_run_are_idempotent():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    article = normalize_article(source="test", title="같은 기사", url="https://example.com/a?utm_source=x")
    with Session(engine) as db:
        repository = NewsRepository(db)
        assert repository.upsert_many([article]) == (1, 0)
        assert repository.upsert_many([article]) == (0, 1)
        assert len(list(db.scalars(select(NewsArticle)))) == 1

        runs = PipelineRunRepository(db)
        first, created = runs.create_or_get(
            job_name="collect-news", idempotency_key="news-20260719", business_date=date(2026, 7, 19),
            trigger_type="test", github_run_id=None, code_version="test",
        )
        second, created_again = runs.create_or_get(
            job_name="collect-news", idempotency_key="news-20260719", business_date=date(2026, 7, 19),
            trigger_type="test", github_run_id=None, code_version="test",
        )
        assert created is True
        assert created_again is False
        assert first.id == second.id
