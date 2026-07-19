from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.economic_event import EconomicEvent


class CalendarRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_many(self, events: list[dict]) -> tuple[int, int]:
        inserted = updated = 0
        for event in events:
            row = self.db.scalar(select(EconomicEvent).where(
                EconomicEvent.source == event["source"], EconomicEvent.source_event_id == event["source_event_id"]
            ))
            values = {key: value for key, value in event.items() if key != "id"}
            if row is None:
                self.db.add(EconomicEvent(**values))
                inserted += 1
            else:
                for key, value in values.items():
                    setattr(row, key, value)
                row.collected_at = datetime.now(timezone.utc)
                updated += 1
        self.db.commit()
        return inserted, updated
