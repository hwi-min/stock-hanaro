import asyncio

from app.realtime.market import MarketStream


class FakeWebSocket:
    def __init__(self):
        self.pongs: list[bytes] = []

    async def pong(self, payload: bytes):
        self.pongs.append(payload)


def test_domestic_stock_tick_is_published_as_realtime():
    stream = MarketStream()
    websocket = FakeWebSocket()
    asyncio.run(stream.handle("0|H0STCNT0|1|005930^091500^81200^2^900^1.12", websocket))

    assert stream.latest["005930"]["price"] == 81200
    assert stream.latest["005930"]["change_pct"] == 1.12
    assert stream.latest["005930"]["basis"] == "realtime"


def test_domestic_index_tick_uses_dashboard_symbol():
    stream = MarketStream()
    websocket = FakeWebSocket()
    fields = ["0001", "091500", "2865.12", "2", "12.34", "0", "0", "0", "0", "0.43"]
    asyncio.run(stream.handle(f"0|H0UPCNT0|1|{'^'.join(fields)}", websocket))

    assert stream.latest["KOSPI"]["price"] == 2865.12
    assert stream.latest["KOSPI"]["change_pct"] == 0.43
    assert stream.latest["KOSPI"]["asset_type"] == "index"


def test_ping_is_answered():
    stream = MarketStream()
    websocket = FakeWebSocket()
    raw = '{"header":{"tr_id":"PINGPONG"}}'
    asyncio.run(stream.handle(raw, websocket))
    assert websocket.pongs == [raw.encode()]


def test_subscription_status_requires_all_acknowledgements(monkeypatch):
    stream = MarketStream()
    websocket = FakeWebSocket()
    monkeypatch.setattr(MarketStream, "expected_subscription_count", property(lambda _: 2))
    first = '{"header":{"tr_id":"H0STCNT0","tr_key":"005930"},"body":{"rt_cd":"0"}}'
    second = '{"header":{"tr_id":"H0UPCNT0","tr_key":"0001"},"body":{"rt_cd":"0"}}'

    asyncio.run(stream.handle(first, websocket))
    assert stream.connected is False
    asyncio.run(stream.handle(second, websocket))
    assert stream.connected is True
