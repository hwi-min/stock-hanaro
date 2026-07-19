from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SourceRef(BaseModel):
    id: str
    label: str


class Briefing(BaseModel):
    stance: Literal["risk_on", "neutral", "risk_off"]
    headline: str
    summary: str
    keywords: list[str]
    source_ids: list[str]
    as_of: datetime


class MarketMetric(BaseModel):
    symbol: str
    label: str
    market: Literal["us", "kr"]
    value: str
    change_pct: float
    as_of: datetime
    stale: bool = False
    basis: Literal["close", "realtime", "delayed"]


class HeatmapItem(BaseModel):
    symbol: str
    name: str
    sector: str
    industry: str
    price: float
    change_pct: float
    market_cap_weight: float


class ScheduleItem(BaseModel):
    id: str
    source: Literal["bls", "bea", "federal_reserve", "bok"]
    country: Literal["US", "KR"]
    category: str
    title: str
    scheduled_at: datetime
    importance: Literal["high", "medium", "low"]
    source_url: str


class RelatedArticle(BaseModel):
    id: str
    title: str
    publisher: str
    published_at: datetime
    url: str
    is_representative: bool = False


class IssueItem(BaseModel):
    id: str
    title: str
    summary: str
    sentiment: Literal["positive", "neutral", "negative"]
    article_count: int
    category: str
    summary_method: Literal["extractive", "source_excerpt", "ai"]
    articles: list[RelatedArticle]


class DisclosureItem(BaseModel):
    id: str
    company: str
    title: str
    importance: Literal["high", "medium", "low"]
    filed_at: datetime
    source_url: str


class KcifSummary(BaseModel):
    id: str
    title: str
    summary: str
    topic: str
    source_url: str
    as_of: datetime


class FreshnessItem(BaseModel):
    dataset: str
    label: str
    as_of: datetime
    stale: bool


class DashboardResponse(BaseModel):
    briefing: Briefing
    metrics: list[MarketMetric]
    heatmap: list[HeatmapItem]
    schedules: list[ScheduleItem]
    issues: list[IssueItem]
    disclosures: list[DisclosureItem]
    kcif: list[KcifSummary]
    freshness: list[FreshnessItem]
