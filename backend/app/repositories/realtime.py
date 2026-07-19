from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.kis import QuotePayload
from app.models.market_quote import MarketQuote
from app.models.realtime import RealtimeSubscription, RealtimeWorkerState
from app.repositories.market import MarketRepository


class RealtimeRepository:
    def __init__(self, db: Session):
        self.db = db

    def acquire(self, symbol: str) -> int:
        row = self.db.get(RealtimeSubscription, symbol)
        if row is None:
            row = RealtimeSubscription(symbol=symbol, viewer_count=1)
            self.db.add(row)
        else:
            row.viewer_count += 1
            row.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return row.viewer_count

    def release(self, symbol: str) -> int:
        row = self.db.get(RealtimeSubscription, symbol)
        if row is None:
            return 0
        row.viewer_count = max(row.viewer_count - 1, 0)
        row.updated_at = datetime.now(timezone.utc)
        if row.viewer_count == 0 and not row.pinned:
            self.db.delete(row)
        self.db.commit()
        return max(row.viewer_count, 0)

    def active_symbols(self) -> set[str]:
        return set(self.db.scalars(select(RealtimeSubscription.symbol).where(
            (RealtimeSubscription.viewer_count > 0) | RealtimeSubscription.pinned
        )).all())

    def save_tick(self, event: dict) -> None:
        MarketRepository(self.db).upsert_many([QuotePayload(
            provider="kis_ws", market="kr", asset_type=event["asset_type"], exchange="KRX",
            symbol=event["symbol"], name=None, sector=None, industry=None, currency="KRW",
            price=Decimal(str(event["price"])), change=Decimal(str(event["change"])),
            change_pct=Decimal(str(event["change_pct"])), volume=None, market_cap=None,
            as_of=datetime.fromisoformat(event["as_of"]),
        )])

    def save_worker_state(self, status: dict) -> None:
        row = self.db.get(RealtimeWorkerState, "kis-market")
        if row is None:
            row = RealtimeWorkerState(name="kis-market")
            self.db.add(row)
        row.connected = bool(status.get("connected"))
        row.configured_stock_count = int(status.get("configured_stock_count", 0))
        row.accepted_subscription_count = int(status.get("accepted_subscription_count", 0))
        last_tick = status.get("last_tick_at")
        row.last_tick_at = datetime.fromisoformat(last_tick) if last_tick else None
        row.last_error = status.get("last_connection_error")
        row.heartbeat_at = datetime.now(timezone.utc)
        self.db.commit()

    def status(self, enabled: bool, configured_stock_count: int = 0) -> dict:
        row = self.db.get(RealtimeWorkerState, "kis-market")
        if row is None:
            return {
                "enabled": enabled, "connected": False, "worker_alive": False,
                "configured_stock_count": configured_stock_count,
                "expected_subscription_count": configured_stock_count + 3,
                "accepted_subscription_count": 0,
            }
        heartbeat = row.heartbeat_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        return {
            "enabled": enabled, "connected": row.connected,
            "worker_alive": heartbeat >= datetime.now(timezone.utc) - timedelta(seconds=45),
            "configured_stock_count": row.configured_stock_count,
            "expected_subscription_count": row.configured_stock_count + 3,
            "accepted_subscription_count": row.accepted_subscription_count,
            "last_tick_at": row.last_tick_at, "last_connection_error": row.last_error,
            "heartbeat_at": heartbeat,
        }

    def latest_ticks(self, max_age_seconds: int = 120) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        rows = self.db.scalars(select(MarketQuote).where(
            MarketQuote.provider == "kis_ws", MarketQuote.market == "kr", MarketQuote.as_of >= cutoff
        )).all()
        return [{
            "symbol": row.symbol, "market": row.market, "asset_type": row.asset_type,
            "price": float(row.price), "change": float(row.change or 0),
            "change_pct": float(row.change_pct or 0), "as_of": row.as_of.isoformat(),
            "basis": "realtime", "provider": row.provider,
        } for row in rows]

    def latest_tick(self, symbol: str, max_age_seconds: int = 120) -> dict | None:
        return next((item for item in self.latest_ticks(max_age_seconds) if item["symbol"] == symbol), None)
