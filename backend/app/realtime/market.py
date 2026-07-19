import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import httpx
import websockets

from app.core.config import settings

INDEX_SUBSCRIPTIONS = {"0001": "KOSPI", "1001": "KOSDAQ", "0128": "KOSPI200"}


def as_number(value: str) -> float:
    try:
        return float(Decimal(value.strip()))
    except (InvalidOperation, ValueError):
        return 0.0


class MarketStream:
    def __init__(self):
        self.latest: dict[str, dict] = {}
        self.subscribers: set[asyncio.Queue] = set()
        self.connected = False
        self.accepted_subscriptions: set[tuple[str, str]] = set()
        self.subscription_errors: list[str] = []
        self.last_connection_error: str | None = None
        self.last_tick_at: str | None = None
        self.pinned_symbols = set(settings.kr_symbols)
        self.desired_symbols = set(settings.kr_symbols)
        self.viewer_counts: dict[str, int] = {}
        self.command_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()

    @property
    def expected_subscriptions(self) -> set[tuple[str, str]]:
        return ({("H0STCNT0", symbol) for symbol in self.desired_symbols}
                | {("H0UPCNT0", code) for code in INDEX_SUBSCRIPTIONS})

    @property
    def expected_subscription_count(self) -> int:
        return len(self.expected_subscriptions)

    def refresh_connection_status(self) -> None:
        self.connected = self.expected_subscriptions.issubset(self.accepted_subscriptions)

    def status(self) -> dict:
        return {
            "enabled": settings.kis_realtime_enabled,
            "connected": self.connected,
            "environment": "mock" if settings.kis_is_mock else "production",
            "configured_stock_count": len(self.desired_symbols),
            "dynamic_stock_count": len(self.desired_symbols - self.pinned_symbols),
            "expected_subscription_count": self.expected_subscription_count,
            "accepted_subscription_count": len(self.accepted_subscriptions),
            "subscription_errors": self.subscription_errors[-5:],
            "last_connection_error": self.last_connection_error,
            "last_tick_at": self.last_tick_at,
        }

    async def approval_key(self) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{settings.kis_base_url}/oauth2/Approval", json={
                "grant_type": "client_credentials", "appkey": settings.kis_app_key,
                "secretkey": settings.kis_app_secret,
            })
            response.raise_for_status()
            return response.json()["approval_key"]

    @staticmethod
    def subscription(approval_key: str, tr_id: str, tr_key: str, tr_type: str = "1") -> str:
        return json.dumps({
            "header": {"approval_key": approval_key, "custtype": "P", "tr_type": tr_type, "content-type": "utf-8"},
            "body": {"input": {"tr_id": tr_id, "tr_key": tr_key}},
        })

    async def acquire(self, symbol: str) -> dict:
        symbol = symbol.strip()
        self.viewer_counts[symbol] = self.viewer_counts.get(symbol, 0) + 1
        if symbol not in self.desired_symbols:
            if len(self.desired_symbols) >= settings.kis_max_realtime_stocks:
                self.viewer_counts[symbol] -= 1
                if self.viewer_counts[symbol] <= 0:
                    self.viewer_counts.pop(symbol, None)
                return {"accepted": False, "reason": "subscription capacity reached", **self.status()}
            self.desired_symbols.add(symbol)
            self.connected = False
            await self.command_queue.put(("1", symbol))
        return {"accepted": True, "symbol": symbol, "viewers": self.viewer_counts[symbol], **self.status()}

    async def release(self, symbol: str) -> dict:
        symbol = symbol.strip()
        count = max(self.viewer_counts.get(symbol, 0) - 1, 0)
        if count:
            self.viewer_counts[symbol] = count
        else:
            self.viewer_counts.pop(symbol, None)
            if symbol not in self.pinned_symbols and symbol in self.desired_symbols:
                self.desired_symbols.remove(symbol)
                self.accepted_subscriptions.discard(("H0STCNT0", symbol))
                await self.command_queue.put(("2", symbol))
        self.refresh_connection_status()
        return {"released": True, "symbol": symbol, "viewers": count, **self.status()}

    async def command_sender(self, websocket, approval_key: str) -> None:
        while True:
            tr_type, symbol = await self.command_queue.get()
            if tr_type == "1" and symbol not in self.desired_symbols:
                continue
            await websocket.send(self.subscription(approval_key, "H0STCNT0", symbol, tr_type))
            await asyncio.sleep(0.06)

    async def publish(self, event: dict) -> None:
        self.latest[event["symbol"]] = event
        for queue in tuple(self.subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            queue.put_nowait(event)

    async def handle(self, raw: str, websocket) -> None:
        if raw.startswith(("0|", "1|")):
            parts = raw.split("|", 3)
            if len(parts) != 4:
                return
            tr_id, payload = parts[1], parts[3].split("^")
            if tr_id == "H0STCNT0" and len(payload) >= 6:
                event = {"symbol": payload[0], "market": "kr", "asset_type": "equity",
                         "price": as_number(payload[2]), "change": as_number(payload[4]),
                         "change_pct": as_number(payload[5])}
            elif tr_id == "H0UPCNT0" and len(payload) >= 10:
                event = {"symbol": INDEX_SUBSCRIPTIONS.get(payload[0], payload[0]), "market": "kr",
                         "asset_type": "index", "price": as_number(payload[2]),
                         "change": as_number(payload[4]), "change_pct": as_number(payload[9])}
            else:
                return
            if event["price"] > 0:
                event.update({"as_of": datetime.now(timezone.utc).isoformat(), "basis": "realtime", "provider": "kis_ws"})
                self.last_tick_at = event["as_of"]
                await self.publish(event)
            return
        try:
            response = json.loads(raw)
        except json.JSONDecodeError:
            return
        if response.get("header", {}).get("tr_id") == "PINGPONG":
            await websocket.pong(raw.encode())
            return
        header = response.get("header", {})
        body = response.get("body", {})
        tr_id, tr_key = header.get("tr_id"), header.get("tr_key")
        if tr_id in {"H0STCNT0", "H0UPCNT0"}:
            if str(body.get("rt_cd", "")) == "0":
                is_unsubscribe = (str(header.get("tr_type", "1")) == "2"
                                  or (tr_id == "H0STCNT0" and tr_key not in self.desired_symbols))
                if is_unsubscribe:
                    self.accepted_subscriptions.discard((tr_id, tr_key or ""))
                else:
                    self.accepted_subscriptions.add((tr_id, tr_key or ""))
                self.refresh_connection_status()
            else:
                message = f"{tr_id}/{tr_key or 'unknown'}: {body.get('msg_cd', 'unknown')} {body.get('msg1', '')}".strip()
                if message not in self.subscription_errors:
                    self.subscription_errors.append(message)

    async def run(self) -> None:
        if not settings.kis_realtime_enabled:
            return
        delay = 1
        while True:
            try:
                self.connected = False
                self.accepted_subscriptions.clear()
                self.subscription_errors.clear()
                while not self.command_queue.empty():
                    try:
                        self.command_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                approval_key = await self.approval_key()
                async with websockets.connect(settings.kis_ws_url, ping_interval=None, close_timeout=5) as websocket:
                    self.last_connection_error = None
                    for symbol in sorted(self.desired_symbols):
                        await websocket.send(self.subscription(approval_key, "H0STCNT0", symbol))
                        await asyncio.sleep(0.06)
                    for code in INDEX_SUBSCRIPTIONS:
                        await websocket.send(self.subscription(approval_key, "H0UPCNT0", code))
                        await asyncio.sleep(0.06)
                    delay = 1
                    sender = asyncio.create_task(self.command_sender(websocket, approval_key))
                    try:
                        async for raw in websocket:
                            await self.handle(raw, websocket)
                    finally:
                        sender.cancel()
                        try:
                            await sender
                        except asyncio.CancelledError:
                            pass
            except asyncio.CancelledError:
                self.connected = False
                raise
            except Exception as exc:
                self.connected = False
                self.last_connection_error = f"{type(exc).__name__}: {str(exc)[:300]}"
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
            else:
                self.connected = False

    async def subscribe(self):
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        try:
            yield {"type": "snapshot", "connected": self.connected, "items": list(self.latest.values())}
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield {"type": "quote", "connected": self.connected, "item": event}
                except asyncio.TimeoutError:
                    yield {"type": "heartbeat", "connected": self.connected}
        finally:
            self.subscribers.discard(queue)


market_stream = MarketStream()
