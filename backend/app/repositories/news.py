from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.news.normalizer import NormalizedNewsArticle
from app.models.news_article import NewsArticle


class NewsRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_many(self, articles: list[NormalizedNewsArticle]) -> tuple[int, int]:
        inserted = skipped = 0
        now = datetime.now(timezone.utc)
        for article in articles:
            existing = self.db.scalar(select(NewsArticle).where(NewsArticle.url_hash == article.url_hash))
            if existing:
                existing.last_seen_at = now
                if article.summary and not existing.summary:
                    existing.summary = article.summary
                    existing.content_hash = article.content_hash
                skipped += 1
                continue
            self.db.add(NewsArticle(**article.__dict__, last_seen_at=now, collected_at=now))
            inserted += 1
        self.db.commit()
        return inserted, skipped
