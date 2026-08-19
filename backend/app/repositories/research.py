from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.collectors.research import ResearchReportPayload
from app.models.research_report import ResearchReport


class ResearchRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_many(self, reports: list[ResearchReportPayload]) -> tuple[int, int]:
        inserted = skipped = 0
        now = datetime.now(timezone.utc)
        for report in reports:
            existing = self.db.scalar(select(ResearchReport).where(
                ResearchReport.source_report_id == report.source_report_id
            ))
            if existing:
                for key, value in report.__dict__.items():
                    setattr(existing, key, value)
                existing.collected_at = now
                skipped += 1
            else:
                self.db.add(ResearchReport(**report.__dict__, collected_at=now))
                inserted += 1
        self.db.commit()
        return inserted, skipped

    def list(self, *, category: str | None = None, broker: str | None = None,
             query: str | None = None, stock_code: str | None = None, limit: int = 100) -> list[ResearchReport]:
        statement = select(ResearchReport)
        if category:
            statement = statement.where(ResearchReport.category == category)
        if broker:
            statement = statement.where(ResearchReport.broker == broker)
        if stock_code:
            statement = statement.where(ResearchReport.stock_code == stock_code)
        if query:
            term = f"%{query.strip()}%"
            statement = statement.where(or_(
                ResearchReport.title.ilike(term), ResearchReport.stock_name.ilike(term),
                ResearchReport.broker.ilike(term), ResearchReport.analyst.ilike(term),
            ))
        return list(self.db.scalars(statement.order_by(
            ResearchReport.published_on.desc(), ResearchReport.id.desc()
        ).limit(limit)))

    def facets(self) -> dict:
        brokers = self.db.execute(select(ResearchReport.broker, func.count()).group_by(
            ResearchReport.broker).order_by(func.count().desc())).all()
        categories = self.db.execute(select(ResearchReport.category, func.count()).group_by(
            ResearchReport.category).order_by(func.count().desc())).all()
        return {"brokers": [{"name": name, "count": count} for name, count in brokers],
                "categories": [{"name": name, "count": count} for name, count in categories]}

