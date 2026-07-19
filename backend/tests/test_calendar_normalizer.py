from datetime import datetime

from app.collectors.calendar import CalendarSource, RawCalendarEvent, normalize_event


def test_us_release_is_converted_to_korea_time():
    event = RawCalendarEvent(
        source=CalendarSource.BLS,
        source_event_id="cpi-2026-07",
        country="US",
        category="물가",
        title="Consumer Price Index (CPI)",
        scheduled_at=datetime(2026, 7, 14, 8, 30),
        source_timezone="America/New_York",
        source_url="https://www.bls.gov/schedule/news_release/cpi.htm",
    )
    result = normalize_event(event)
    assert result["scheduled_at_utc"].hour == 12
    assert result["scheduled_at_kst"].hour == 21
    assert result["importance"] == "high"


def test_normalized_id_is_stable():
    event = RawCalendarEvent(
        source=CalendarSource.BOK,
        source_event_id="bok-gdp-q2",
        country="KR",
        category="성장",
        title="2분기 실질 국내총생산 속보",
        scheduled_at=datetime(2026, 7, 23, 8, 0),
        source_timezone="Asia/Seoul",
        source_url="https://www.bok.or.kr/",
    )
    assert normalize_event(event)["id"] == normalize_event(event)["id"]
