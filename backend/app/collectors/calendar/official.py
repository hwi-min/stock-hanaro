import calendar
import hashlib
import re
from datetime import datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

from app.collectors.calendar.normalizer import CalendarSource, RawCalendarEvent, normalize_event
from app.core.config import settings


BLS_ICS_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BEA_ICS_URL = "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics"
FED_BASE_URL = "https://www.federalreserve.gov/newsevents/"
BOK_URL = "https://www.bok.or.kr/portal/stats/statsPublictSchdul/listCldr.do"


def unfold_ics(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith((" ", "\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def parse_ics_datetime(value: str) -> tuple[datetime, str]:
    raw = value.strip()
    if raw.endswith("Z"):
        return datetime.strptime(raw, "%Y%m%dT%H%M%SZ"), "UTC"
    if "T" in raw:
        return datetime.strptime(raw, "%Y%m%dT%H%M%S"), "America/New_York"
    return datetime.strptime(raw, "%Y%m%d"), "America/New_York"


def parse_ics(text: str, source: CalendarSource, source_url: str) -> list[dict]:
    events: list[dict] = []
    current: dict[str, str] | None = None
    for line in unfold_ics(text):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current:
            title = current.get("SUMMARY", "").replace("\\,", ",").replace("\\n", " ").strip()
            start = current.get("DTSTART")
            if title and start:
                scheduled_at, timezone_name = parse_ics_datetime(start)
                uid = current.get("UID") or hashlib.sha256(f"{title}:{start}".encode()).hexdigest()[:24]
                events.append(normalize_event(RawCalendarEvent(
                    source=source, source_event_id=uid, country="US", category="경제지표", title=title,
                    scheduled_at=scheduled_at, source_timezone=timezone_name, source_url=source_url,
                )))
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";", 1)[0]] = value
    return events


def parse_fed_month(html: str, year: int, month: int, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    events: list[dict] = []
    for title_node in soup.select(".calendar__title"):
        row = title_node.find_parent("div", class_="row")
        if row is None:
            continue
        columns = row.find_all("div", recursive=False)
        if len(columns) < 3:
            continue
        time_text = columns[0].get_text(" ", strip=True)
        day_match = re.search(r"\b(\d{1,2})\b", columns[-1].get_text(" ", strip=True))
        time_match = re.search(r"(\d{1,2}):(\d{2})\s*([ap])\.m\.", time_text, re.I)
        if not day_match or not time_match:
            continue
        hour, minute = int(time_match.group(1)), int(time_match.group(2))
        if time_match.group(3).lower() == "p" and hour != 12:
            hour += 12
        if time_match.group(3).lower() == "a" and hour == 12:
            hour = 0
        title = title_node.get_text(" ", strip=True)
        day = int(day_match.group(1))
        identity = hashlib.sha256(f"{year}-{month}-{day}:{time_text}:{title}".encode()).hexdigest()[:24]
        events.append(normalize_event(RawCalendarEvent(
            source=CalendarSource.FEDERAL_RESERVE, source_event_id=identity, country="US", category="연준",
            title=title, scheduled_at=datetime(year, month, day, hour, minute),
            source_timezone="America/New_York", source_url=source_url,
        )))
    return events


def parse_bok(html: str, source_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    events: list[dict] = []
    tables = soup.select("table")
    if not tables:
        return events
    rows = tables[-1].select("tbody tr") or tables[-1].select("tr")[1:]
    for row in rows:
        cells = [cell.get_text(" ", strip=True) for cell in row.select("th,td")]
        if len(cells) < 3 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
            continue
        try:
            scheduled_at = datetime.strptime(f"{cells[0]} {cells[1]}", "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        title = cells[2]
        identity = hashlib.sha256(f"{cells[0]}:{cells[1]}:{title}".encode()).hexdigest()[:24]
        events.append(normalize_event(RawCalendarEvent(
            source=CalendarSource.BOK, source_event_id=identity, country="KR", category="경제지표",
            title=title, scheduled_at=scheduled_at, source_timezone="Asia/Seoul", source_url=source_url,
        )))
    return events


class OfficialCalendarCollector:
    async def collect(self, reference: datetime | None = None) -> tuple[list[dict], list[str]]:
        reference = reference or datetime.now(ZoneInfo("Asia/Seoul"))
        events, errors = [], []
        headers = {"User-Agent": settings.news_user_agent}
        async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers=headers) as client:
            for source, url in ((CalendarSource.BLS, BLS_ICS_URL), (CalendarSource.BEA, BEA_ICS_URL)):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    events.extend(parse_ics(response.text, source, url))
                except Exception as exc:
                    errors.append(f"{source.value}: {exc}")
            for offset in (0, 1):
                month = reference.month + offset
                year = reference.year + (month - 1) // 12
                month = (month - 1) % 12 + 1
                fed_url = urljoin(FED_BASE_URL, f"{year}-{calendar.month_name[month].lower()}.htm")
                try:
                    response = await client.get(fed_url)
                    response.raise_for_status()
                    events.extend(parse_fed_month(response.text, year, month, fed_url))
                except Exception as exc:
                    errors.append(f"federal_reserve:{year}-{month:02d}: {exc}")
            bok_url = f"{BOK_URL}?date={reference.year}-{reference.month:02d}&menuNo=200775"
            try:
                response = await client.get(bok_url)
                response.raise_for_status()
                events.extend(parse_bok(response.text, bok_url))
            except Exception as exc:
                errors.append(f"bok: {exc}")
        unique = {(event["source"], event["source_event_id"]): event for event in events}
        return list(unique.values()), errors
