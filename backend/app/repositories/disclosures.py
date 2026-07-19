from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.dart import DisclosurePayload
from app.models.disclosure import Disclosure


class DisclosureRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_many(self, disclosures: list[DisclosurePayload]) -> tuple[int, int]:
        inserted = skipped = 0
        for disclosure in disclosures:
            existing = self.db.scalar(select(Disclosure).where(Disclosure.receipt_no == disclosure.receipt_no))
            if existing:
                for key, value in disclosure.__dict__.items():
                    setattr(existing, key, value)
                skipped += 1
            else:
                self.db.add(Disclosure(**disclosure.__dict__))
                inserted += 1
        self.db.commit()
        return inserted, skipped
