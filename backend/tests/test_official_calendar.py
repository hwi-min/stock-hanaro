from app.collectors.calendar.normalizer import CalendarSource
from app.collectors.calendar.official import parse_bok, parse_fed_month, parse_ics


def test_parse_official_ics():
    text = """BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Consumer Price Index
DTSTART:20260714T123000Z
UID:cpi-2026-07
END:VEVENT
END:VCALENDAR"""
    events = parse_ics(text, CalendarSource.BLS, "https://example.com/bls.ics")
    assert events[0]["source_event_id"] == "cpi-2026-07"
    assert events[0]["scheduled_at_kst"].hour == 21
    assert events[0]["importance"] == "high"


def test_parse_federal_reserve_month():
    html = """<div class="row"><div class="col-xs-2"><p>2:30 p.m.</p></div>
    <div class="col-xs-7"><p class="calendar__title">Economic Outlook</p></div>
    <div class="col-xs-3"><p>16</p></div></div>"""
    events = parse_fed_month(html, 2026, 7, "https://example.com/fed")
    assert len(events) == 1
    assert events[0]["scheduled_at_utc"].hour == 18


def test_parse_bank_of_korea_table():
    html = """<table><thead><tr><th>공표일</th><th>시각</th><th>대상통계</th></tr></thead><tbody>
    <tr><td>2026-07-23</td><td>8:00</td><td>2026년 2/4분기 실질 국내총생산(속보)</td></tr>
    </tbody></table>"""
    events = parse_bok(html, "https://example.com/bok")
    assert len(events) == 1
    assert events[0]["scheduled_at_kst"].hour == 8
    assert events[0]["importance"] == "high"
