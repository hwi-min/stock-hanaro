from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.kcif import KcifReportPayload
from app.models.kcif_report import KcifReport


class KcifRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert(self, report: KcifReportPayload) -> tuple[int, int]:
        existing = self.db.scalar(select(KcifReport).where(KcifReport.report_no == report.report_no))
        if existing:
            return 0, 1
        self.db.add(KcifReport(**report.__dict__))
        self.db.commit()
        return 1, 0
