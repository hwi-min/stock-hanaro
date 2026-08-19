from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.research import ResearchRepository

router = APIRouter(prefix="/research", tags=["research"])


def serialize(report):
    return {
        "id": report.id, "source": report.source, "source_report_id": report.source_report_id,
        "category": report.category, "title": report.title, "broker": report.broker,
        "analyst": report.analyst, "published_on": report.published_on,
        "stock_code": report.stock_code, "stock_name": report.stock_name,
        "opinion": report.opinion, "target_price": report.target_price,
        "previous_target_price": report.previous_target_price, "source_url": report.source_url,
    }


@router.get("")
def list_reports(category: str | None = None, broker: str | None = None, q: str | None = None,
                 stock_code: str | None = None, limit: int = Query(100, ge=1, le=200),
                 db: Session = Depends(get_db)):
    repository = ResearchRepository(db)
    reports = repository.list(category=category, broker=broker, query=q, stock_code=stock_code, limit=limit)
    return {"items": [serialize(report) for report in reports], "facets": repository.facets()}

