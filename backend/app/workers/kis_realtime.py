import asyncio
from contextlib import suppress

from app.core.config import settings
from app.core.database import SessionLocal
from app.realtime.market import MarketStream
from app.repositories.realtime import RealtimeRepository


async def persist_event(event: dict) -> None:
    def save() -> None:
        with SessionLocal() as db:
            RealtimeRepository(db).save_tick(event)

    await asyncio.to_thread(save)


async def synchronize_subscriptions(stream: MarketStream) -> None:
    while True:
        with SessionLocal() as db:
            requested = RealtimeRepository(db).active_symbols()
        target = set(settings.kr_symbols) | requested
        for symbol in sorted(target - stream.desired_symbols):
            if len(stream.desired_symbols) >= settings.kis_max_realtime_stocks:
                break
            stream.desired_symbols.add(symbol)
            stream.connected = False
            await stream.command_queue.put(("1", symbol))
        for symbol in sorted(stream.desired_symbols - target):
            stream.desired_symbols.remove(symbol)
            stream.accepted_subscriptions.discard(("H0STCNT0", symbol))
            await stream.command_queue.put(("2", symbol))
        stream.refresh_connection_status()
        await asyncio.sleep(2)


async def publish_heartbeat(stream: MarketStream) -> None:
    while True:
        with SessionLocal() as db:
            RealtimeRepository(db).save_worker_state(stream.status())
        await asyncio.sleep(15)


async def run() -> None:
    stream = MarketStream(event_sink=persist_event)
    if not settings.kis_realtime_enabled:
        with SessionLocal() as db:
            RealtimeRepository(db).save_worker_state(stream.status())
        return
    tasks = [
        asyncio.create_task(stream.run()),
        asyncio.create_task(synchronize_subscriptions(stream)),
        asyncio.create_task(publish_heartbeat(stream)),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task


if __name__ == "__main__":
    asyncio.run(run())
