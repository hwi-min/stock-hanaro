import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.market_catalog import KR_STOCKS
from app.realtime import market_stream
from app.repositories.stock_master import StockMasterRepository

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/status")
def market_status():
    return market_stream.status()


def validate_domestic_symbol(symbol: str, db: Session) -> str:
    symbol = symbol.strip()
    if symbol not in KR_STOCKS and StockMasterRepository(db).find(symbol) is None:
        raise HTTPException(status_code=404, detail="domestic stock symbol not found")
    return symbol


@router.post("/subscriptions/{symbol}")
async def acquire_subscription(symbol: str, db: Session = Depends(get_db)):
    result = await market_stream.acquire(validate_domestic_symbol(symbol, db))
    if not result["accepted"]:
        raise HTTPException(status_code=409, detail=result)
    return result


@router.delete("/subscriptions/{symbol}")
async def release_subscription(symbol: str, db: Session = Depends(get_db)):
    return await market_stream.release(validate_domestic_symbol(symbol, db))


@router.get("/stream")
async def stream_market():
    async def events():
        async for event in market_stream.subscribe():
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })
