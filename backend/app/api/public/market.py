import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.realtime import market_stream

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/status")
def market_status():
    return market_stream.status()


@router.get("/stream")
async def stream_market():
    async def events():
        async for event in market_stream.subscribe():
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
    })
