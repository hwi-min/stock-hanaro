from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.collectors.stock_master import StockMasterPayload
from app.models.stock_master import StockMaster


class StockMasterRepository:
    def __init__(self, db: Session):
        self.db = db

    def replace(self, items: list[StockMasterPayload]) -> tuple[int, int]:
        markets = {item.market for item in items}
        self.db.execute(update(StockMaster).where(StockMaster.market.in_(markets)).values(active=False))
        inserted = updated = 0
        for item in items:
            row = self.db.scalar(select(StockMaster).where(StockMaster.symbol == item.symbol))
            if row is None:
                self.db.add(StockMaster(**item.__dict__))
                inserted += 1
            else:
                row.isin, row.name, row.market = item.isin, item.name, item.market
                row.product_type, row.active = item.product_type, True
                row.collected_at = item.collected_at
                row.updated_at = datetime.now(timezone.utc)
                updated += 1
        self.db.commit()
        return inserted, updated

    def find(self, symbol: str) -> StockMaster | None:
        return self.db.scalar(select(StockMaster).where(StockMaster.symbol == symbol, StockMaster.active.is_(True)))

    def search(self, term: str, limit: int = 10) -> list[StockMaster]:
        pattern = f"%{term}%"
        return list(self.db.scalars(select(StockMaster).where(
            StockMaster.active.is_(True),
            (StockMaster.symbol.ilike(pattern) | StockMaster.name.ilike(pattern)),
        ).order_by(StockMaster.symbol.startswith(term).desc(), StockMaster.name).limit(limit)))
