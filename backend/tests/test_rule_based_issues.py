from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.issue_summary import IssueSummary
from app.models.news_article import NewsArticle
from app.models.stock_master import StockMaster
from app.repositories.dashboard import DashboardRepository
from app.services.rule_based_issues import RULE_MODEL, RuleBasedIssueService


def article(*, title: str, summary: str, publisher: str, url_hash: str, published_at: datetime) -> NewsArticle:
    return NewsArticle(source="test", publisher=publisher, title=title, summary=summary,
                       canonical_url=f"https://example.com/{url_hash}", url_hash=url_hash,
                       content_hash=f"content-{url_hash}", published_at=published_at,
                       first_seen_at=published_at, last_seen_at=published_at, collected_at=published_at)


def test_rule_based_issue_clusters_corroborated_articles_and_extracts_source_sentences():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add(StockMaster(symbol="005930", isin="KR7005930003", name="삼성전자", market="KOSPI",
                           product_type="ST", active=True, collected_at=now, updated_at=now))
        db.add_all([
            article(title="삼성전자 HBM 공급 확대", publisher="경제A", url_hash="a", published_at=now,
                    summary="삼성전자가 HBM 공급 확대를 추진한다고 밝혔다. 하반기 생산량을 20% 늘릴 계획이다."),
            article(title="삼성전자 HBM 고객사 공급 임박", publisher="경제B", url_hash="b",
                    published_at=now - timedelta(minutes=20),
                    summary="삼성전자 HBM 제품의 고객사 공급이 임박했다. 품질 테스트가 진행 중이다."),
            article(title="국제유가 소폭 상승", publisher="경제C", url_hash="c",
                    published_at=now - timedelta(minutes=30), summary="WTI 가격이 소폭 상승했다."),
        ])
        db.commit()

        assert RuleBasedIssueService(db).run(now=now) == 1
        issue = db.scalar(select(IssueSummary))
        assert issue is not None
        assert issue.model == RULE_MODEL
        assert issue.category == "반도체"
        assert "삼성전자" in issue.summary
        assert "국제유가" not in issue.summary

        dashboard_issue = DashboardRepository(db).issues()[0]
        assert dashboard_issue["article_count"] == 2
        assert dashboard_issue["summary_method"] == "extractive"
        assert dashboard_issue["articles"][0]["is_representative"] is True


def test_rule_based_issue_does_not_publish_single_source_pair():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        db.add_all([
            article(title="연준 금리 인하 전망", publisher="경제A", url_hash="a", published_at=now,
                    summary="연준의 금리 인하 가능성이 제기됐다."),
            article(title="FOMC 금리 인하 논의", publisher="경제A", url_hash="b",
                    published_at=now - timedelta(minutes=10), summary="FOMC에서 금리 인하를 논의했다."),
        ])
        db.commit()

        assert RuleBasedIssueService(db).run(now=now) == 0
        assert db.scalar(select(IssueSummary)) is None
