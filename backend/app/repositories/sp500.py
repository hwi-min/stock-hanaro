from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.collectors.sp500 import Sp500ConstituentPayload
from app.models.sp500 import Sp500Constituent, Sp500DailySnapshot


class Sp500Repository:
    def __init__(self, db: Session):
        self.db = db

    def replace_constituents(self, items: list[Sp500ConstituentPayload]) -> tuple[int, int]:
        symbols = {item.symbol for item in items}
        existing = {row.symbol: row for row in self.db.scalars(select(Sp500Constituent)).all()}
        inserted = updated = 0
        for symbol, row in existing.items():
            row.active = symbol in symbols
        for item in items:
            row = existing.get(item.symbol)
            values = item.__dict__
            if row is None:
                self.db.add(Sp500Constituent(**values, active=True))
                inserted += 1
            else:
                for key, value in values.items():
                    setattr(row, key, value)
                row.active = True
                row.updated_at = datetime.now(timezone.utc)
                updated += 1
        self.db.commit()
        return inserted, updated

    def active_constituents(self) -> list[Sp500Constituent]:
        return list(self.db.scalars(select(Sp500Constituent).where(Sp500Constituent.active.is_(True)).order_by(Sp500Constituent.symbol)))

    def snapshot_symbols(self, trading_date: date) -> set[str]:
        return set(self.db.scalars(select(Sp500DailySnapshot.symbol).where(Sp500DailySnapshot.trading_date == trading_date)))

    def latest_complete_date(self, minimum_ratio: Decimal = Decimal("0.98")) -> date | None:
        active_count = self.db.scalar(select(func.count()).select_from(Sp500Constituent).where(Sp500Constituent.active.is_(True))) or 0
        if not active_count:
            return None
        rows = self.db.execute(select(
            Sp500DailySnapshot.trading_date, func.count(Sp500DailySnapshot.id)
        ).group_by(Sp500DailySnapshot.trading_date).order_by(Sp500DailySnapshot.trading_date.desc())).all()
        return next((trading_date for trading_date, count in rows if Decimal(count) / Decimal(active_count) >= minimum_ratio), None)

    def upsert_snapshots(self, items: list[dict]) -> tuple[int, int]:
        inserted = updated = 0
        for item in items:
            row = self.db.scalar(select(Sp500DailySnapshot).where(
                Sp500DailySnapshot.trading_date == item["trading_date"], Sp500DailySnapshot.symbol == item["symbol"]
            ))
            if row is None:
                self.db.add(Sp500DailySnapshot(**item))
                inserted += 1
            else:
                for key, value in item.items():
                    setattr(row, key, value)
                row.collected_at = datetime.now(timezone.utc)
                updated += 1
        cutoff = date.today() - timedelta(days=90)
        self.db.execute(delete(Sp500DailySnapshot).where(Sp500DailySnapshot.trading_date < cutoff))
        self.db.commit()
        return inserted, updated
