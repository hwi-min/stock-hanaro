from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.kis import QuotePayload
from app.models.market_quote import MarketQuote


class MarketRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_many(self, quotes: list[QuotePayload]) -> tuple[int, int]:
        inserted = updated = 0
        for quote in quotes:
            row = self.db.scalar(select(MarketQuote).where(
                MarketQuote.provider == quote.provider, MarketQuote.market == quote.market,
                MarketQuote.symbol == quote.symbol,
            ))
            if row is None:
                self.db.add(MarketQuote(**quote.__dict__))
                inserted += 1
            else:
                for key, value in quote.__dict__.items():
                    setattr(row, key, value)
                row.collected_at = datetime.now(timezone.utc)
                updated += 1
        self.db.commit()
        return inserted, updated
