from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.market_freshness import domestic_chart_ttl, domestic_market_code, domestic_quote_ttl


KST = ZoneInfo("Asia/Seoul")


def at(hour: int, minute: int, weekday_day: int = 24) -> datetime:
    return datetime(2026, 8, weekday_day, hour, minute, tzinfo=KST)


def test_domestic_quote_ttl_follows_market_sessions():
    assert domestic_quote_ttl(at(8, 10)) == 30
    assert domestic_quote_ttl(at(8, 55)) == 60
    assert domestic_quote_ttl(at(10, 0)) == 10
    assert domestic_quote_ttl(at(10, 0), surface="home") == 30
    assert domestic_quote_ttl(at(16, 0)) == 30
    assert domestic_quote_ttl(at(16, 0), surface="home") == 60
    assert domestic_quote_ttl(at(21, 0)) == 12 * 60 * 60


def test_domestic_quote_ttl_uses_closed_policy_on_weekends():
    saturday = at(10, 0, weekday_day=29)
    assert domestic_quote_ttl(saturday) == 12 * 60 * 60
    assert domestic_chart_ttl(saturday) == 12 * 60 * 60


def test_domestic_chart_is_cached_for_five_minutes_during_market_hours():
    assert domestic_chart_ttl(at(10, 0)) == 5 * 60


def test_domestic_market_code_uses_nxt_only_during_nxt_sessions():
    assert domestic_market_code(at(8, 10)) == "NX"
    assert domestic_market_code(at(8, 55)) == "J"
    assert domestic_market_code(datetime(2026, 8, 24, 9, 0, 29, tzinfo=KST)) == "J"
    assert domestic_market_code(datetime(2026, 8, 24, 9, 0, 30, tzinfo=KST)) == "NX"
    assert domestic_market_code(at(15, 25)) == "J"
    assert domestic_market_code(at(16, 0)) == "NX"
    assert domestic_market_code(at(20, 0)) == "J"
    assert domestic_market_code(at(10, 0, weekday_day=29)) == "J"
