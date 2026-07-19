from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo


class CalendarSource(StrEnum):
    BLS = "bls"
    BEA = "bea"
    FEDERAL_RESERVE = "federal_reserve"
    BOK = "bok"


@dataclass(frozen=True)
class RawCalendarEvent:
    source: CalendarSource
    source_event_id: str
    country: str
    category: str
    title: str
    scheduled_at: datetime
    source_timezone: str
    source_url: str


HIGH_KEYWORDS = (
    "cpi", "consumer price", "소비자물가", "pce", "employment situation", "고용보고서",
    "gross domestic product", "gdp", "국내총생산", "fomc", "금리 결정", "통화정책방향",
)
MEDIUM_KEYWORDS = (
    "ppi", "producer price", "생산자물가", "retail sales", "소매판매", "industrial production",
    "산업생산", "consumer confidence", "소비자심리", "speech", "연설", "국제수지",
)


def classify_importance(title: str) -> str:
    normalized = title.casefold()
    if any(keyword in normalized for keyword in HIGH_KEYWORDS):
        return "high"
    if any(keyword in normalized for keyword in MEDIUM_KEYWORDS):
        return "medium"
    return "low"


def normalize_event(event: RawCalendarEvent) -> dict:
    source_zone = ZoneInfo(event.source_timezone)
    scheduled = event.scheduled_at
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=source_zone)
    scheduled_utc = scheduled.astimezone(ZoneInfo("UTC"))
    scheduled_kst = scheduled.astimezone(ZoneInfo("Asia/Seoul"))
    identity = f"{event.source}:{event.source_event_id}:{scheduled_utc.isoformat()}"
    return {
        "id": hashlib.sha256(identity.encode()).hexdigest()[:20],
        "source": event.source.value,
        "source_event_id": event.source_event_id,
        "country": event.country,
        "category": event.category,
        "title": event.title.strip(),
        "scheduled_at_utc": scheduled_utc,
        "scheduled_at_kst": scheduled_kst,
        "importance": classify_importance(event.title),
        "source_url": event.source_url,
    }
