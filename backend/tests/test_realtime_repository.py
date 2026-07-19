from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.core.database import Base
from app.repositories.realtime import RealtimeRepository


def repository(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'realtime.db'}")
    Base.metadata.create_all(engine)
    return engine


def test_subscription_is_shared_and_released(tmp_path):
    engine = repository(tmp_path)
    with Session(engine, expire_on_commit=False) as db:
        realtime = RealtimeRepository(db)
        assert realtime.acquire("005930") == 1
        assert realtime.acquire("005930") == 2
        assert realtime.active_symbols() == {"005930"}
        assert realtime.release("005930") == 1
        assert realtime.release("005930") == 0
        assert realtime.active_symbols() == set()


def test_worker_tick_and_heartbeat_are_shared_through_database(tmp_path):
    engine = repository(tmp_path)
    now = datetime.now(timezone.utc).isoformat()
    with Session(engine, expire_on_commit=False) as db:
        realtime = RealtimeRepository(db)
        realtime.save_tick({
            "symbol": "005930", "market": "kr", "asset_type": "equity",
            "price": 81200, "change": 900, "change_pct": 1.12, "as_of": now,
        })
        realtime.save_worker_state({
            "connected": True, "configured_stock_count": 4,
            "accepted_subscription_count": 7, "last_tick_at": now,
            "last_connection_error": None,
        })

        assert realtime.latest_ticks()[0]["price"] == 81200
        status = realtime.status(enabled=True, configured_stock_count=4)
        assert status["connected"] is True
        assert status["worker_alive"] is True
