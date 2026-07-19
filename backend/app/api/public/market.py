import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.market_catalog import KR_STOCKS
from app.core.config import settings
from app.core.database import SessionLocal
from app.repositories.realtime import RealtimeRepository
from app.repositories.stock_master import StockMasterRepository

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/status")
def market_status(db: Session = Depends(get_db)):
    return RealtimeRepository(db).status(settings.kis_realtime_enabled, len(settings.kr_symbols))


def validate_domestic_symbol(symbol: str, db: Session) -> str:
    symbol = symbol.strip()
    if symbol not in KR_STOCKS and StockMasterRepository(db).find(symbol) is None:
        raise HTTPException(status_code=404, detail="domestic stock symbol not found")
    return symbol


@router.post("/subscriptions/{symbol}")
def acquire_subscription(symbol: str, db: Session = Depends(get_db)):
    symbol = validate_domestic_symbol(symbol, db)
    repository = RealtimeRepository(db)
    active = repository.active_symbols() | set(settings.kr_symbols)
    if symbol not in active and len(active) >= settings.kis_max_realtime_stocks:
        raise HTTPException(status_code=409, detail="realtime subscription capacity reached")
    viewers = repository.acquire(symbol)
    return {"accepted": True, "symbol": symbol, "viewers": viewers}


@router.delete("/subscriptions/{symbol}")
def release_subscription(symbol: str, db: Session = Depends(get_db)):
    symbol = validate_domestic_symbol(symbol, db)
    return {"released": True, "symbol": symbol, "viewers": RealtimeRepository(db).release(symbol)}


@router.get("/stream")
async def stream_market():
    async def events():
        previous: dict[str, str] = {}
        initialized = False
        while True:
            with SessionLocal() as db:
                repository = RealtimeRepository(db)
                items = repository.latest_ticks(settings.realtime_tick_max_age_seconds)
                status = repository.status(settings.kis_realtime_enabled, len(settings.kr_symbols))
            changed = [item for item in items if previous.get(item["symbol"]) != item["as_of"]]
            if not initialized:
                payload = {"type": "snapshot", "connected": status["connected"], "items": items}
                initialized = True
            elif changed:
                payload = {"type": "quote", "connected": status["connected"], "items": changed}
            else:
                payload = {"type": "heartbeat", "connected": status["connected"]}
            previous.update({item["symbol"]: item["as_of"] for item in items})
            yield f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
            await asyncio.sleep(1 if changed else 5)

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })
