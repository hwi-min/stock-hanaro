import re
import json
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.disclosure import Disclosure
from app.models.economic_event import EconomicEvent
from app.models.kcif_report import KcifReport
from app.models.market_quote import MarketQuote
from app.models.news_article import NewsArticle
from app.models.issue_summary import IssueSummary
from app.models.research_report import ResearchReport


METRIC_ORDER = ("SPX", "DOW30", "NASDAQ", "RUSSELL2000", "VIX", "GOLD", "KOSPI", "KOSDAQ", "KOSPI200", "USDKRW", "KTB3Y")
METRIC_LABELS = {
    "SPX": "S&P 500", "DOW30": "Dow 30", "NASDAQ": "NASDAQ", "RUSSELL2000": "Russell 2000",
    "VIX": "VIX", "GOLD": "Gold", "KOSPI": "KOSPI", "KOSDAQ": "KOSDAQ", "KOSPI200": "KOSPI 200",
    "USDKRW": "USD/KRW", "KTB3Y": "국고채 3년",
}

KST = ZoneInfo("Asia/Seoul")


def current_week_bounds_utc(now: datetime) -> tuple[datetime, datetime]:
    """Return the KST Monday-to-Monday range containing ``now`` in UTC."""
    now_kst = now.astimezone(KST)
    monday = now_kst.date() - timedelta(days=now_kst.weekday())
    start_kst = datetime.combine(monday, time.min, tzinfo=KST)
    return start_kst.astimezone(timezone.utc), (start_kst + timedelta(days=7)).astimezone(timezone.utc)


def aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=timezone.utc)


def number(value: Decimal | None) -> float:
    return float(value or 0)


class DashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def market_metrics(self) -> list[dict]:
        rows = self.db.scalars(select(MarketQuote).where(MarketQuote.symbol.in_(METRIC_ORDER))).all()
        by_symbol = {row.symbol: row for row in rows}
        result = []
        for symbol in METRIC_ORDER:
            row = by_symbol.get(symbol)
            if row is None or row.price <= 0:
                continue
            value = f"{number(row.price):,.3f}" if symbol == "KTB3Y" else f"{number(row.price):,.2f}"
            if symbol == "KTB3Y":
                value += "%"
            result.append({
                "symbol": symbol, "label": METRIC_LABELS[symbol],
                "market": "us" if row.market in {"us", "global"} else "kr", "value": value,
                "change_pct": number(row.change_pct), "as_of": aware(row.as_of),
                "stale": datetime.now(timezone.utc) - aware(row.collected_at) > timedelta(minutes=30),
                "basis": "close" if row.market in {"us", "global"} else "delayed",
            })
        return result

    def heatmap(self) -> list[dict]:
        rows = self.db.scalars(select(MarketQuote).where(
            MarketQuote.market == "us", MarketQuote.asset_type == "equity",
        ).order_by(desc(MarketQuote.market_cap))).all()
        caps = [number(row.market_cap) for row in rows if number(row.market_cap) > 0]
        max_cap = max(caps, default=1)
        return [{
            "symbol": row.symbol, "name": row.name or row.symbol, "sector": row.sector or "기타",
            "industry": row.industry or "기타", "price": number(row.price), "change_pct": number(row.change_pct),
            "market_cap_weight": max(1.0, number(row.market_cap) / max_cap * 24) if row.market_cap else 1.0,
        } for row in rows]

    def schedules(self, now: datetime) -> list[dict]:
        start, end = current_week_bounds_utc(now)
        rows = self.db.scalars(select(EconomicEvent).where(
            EconomicEvent.scheduled_at_utc >= start, EconomicEvent.scheduled_at_utc < end,
        ).order_by(EconomicEvent.scheduled_at_utc)).all()
        return [{
            "id": f"{row.source}:{row.source_event_id}", "source": row.source, "country": row.country,
            "category": row.category, "title": row.title, "scheduled_at": aware(row.scheduled_at_kst),
            "importance": row.importance, "source_url": row.source_url,
        } for row in rows]

    @staticmethod
    def _news_category(title: str) -> str:
        compact = title.lower()
        for keywords, category in ((('반도체', 'hbm', 'ai'), '반도체'), (('금리', '연준', 'fed'), '거시·금리'),
                                   (('유가', '원유', 'oil'), '에너지'), (('환율', '달러'), '환율'),
                                   (('중국',), '중국'), (('코스피', '증시'), '증시')):
            if any(keyword in compact for keyword in keywords):
                return category
        return "주요 뉴스"

    def issues(self) -> list[dict]:
        generated_rows = self.db.scalars(select(IssueSummary).order_by(desc(IssueSummary.generated_at))).all()
        generated_result = []
        for generated in generated_rows:
            try:
                article_ids = [int(value) for value in json.loads(generated.article_ids_json)]
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            by_id = {row.id: row for row in self.db.scalars(select(NewsArticle).where(
                NewsArticle.id.in_(article_ids),
            )).all()}
            articles = [by_id[value] for value in article_ids if value in by_id]
            if not articles:
                continue
            generated_result.append({
                "id": generated.issue_key, "title": generated.title, "summary": generated.summary,
                "sentiment": generated.sentiment, "article_count": len(articles), "category": generated.category,
                "summary_method": "extractive" if generated.model == "rule-based-extractive" else "ai",
                "articles": [{
                    "id": str(row.id), "title": row.title, "publisher": row.publisher or row.source,
                    "published_at": aware(row.published_at or row.collected_at), "url": row.canonical_url,
                    "is_representative": index == 0,
                } for index, row in enumerate(articles)],
            })
            if len(generated_result) == 6:
                break
        if generated_result:
            return generated_result

        rows = self.db.scalars(select(NewsArticle).order_by(
            desc(NewsArticle.published_at), desc(NewsArticle.collected_at),
        ).limit(30)).all()
        groups: dict[str, list[NewsArticle]] = {}
        for row in rows:
            groups.setdefault(self._news_category(row.title), []).append(row)
        slugs = {"반도체": "semiconductor", "거시·금리": "macro-rates", "에너지": "energy",
                 "환율": "fx", "중국": "china", "증시": "market", "주요 뉴스": "news"}
        result = []
        generated_by_key = {row.issue_key: row for row in self.db.scalars(select(IssueSummary)).all()}
        for category, articles in list(groups.items())[:6]:
            representative = articles[0]
            issue_key = slugs[category]
            generated = generated_by_key.get(issue_key)
            result.append({
                "id": issue_key, "title": generated.title if generated else representative.title,
                "summary": generated.summary if generated else representative.summary or representative.title,
                "sentiment": generated.sentiment if generated else "neutral",
                "article_count": len(articles), "category": category,
                "summary_method": "ai" if generated else "source_excerpt",
                "articles": [{
                    "id": str(row.id), "title": row.title, "publisher": row.publisher or row.source,
                    "published_at": aware(row.published_at or row.collected_at), "url": row.canonical_url,
                    "is_representative": index == 0,
                } for index, row in enumerate(articles[:8])],
            })
        return result

    def disclosures(self) -> list[dict]:
        latest_date = self.db.scalar(select(func.max(Disclosure.receipt_date)))
        if latest_date is None:
            return []
        rows = self.db.scalars(select(Disclosure).where(
            Disclosure.receipt_date == latest_date, Disclosure.importance.in_(("high", "medium")),
        ).order_by(
            desc(Disclosure.importance), desc(Disclosure.receipt_no),
        ).limit(10)).all()
        return [{
            "id": row.receipt_no, "company": row.corp_name, "title": row.title.strip(),
            "importance": row.importance,
            "filed_at": datetime.combine(row.receipt_date, time.min, tzinfo=timezone.utc),
            "source_url": row.source_url,
        } for row in rows]

    @staticmethod
    def _kcif_topic(title: str) -> str:
        for keyword, topic in (("금리", "금리"), ("환율", "환율"), ("유가", "원자재"), ("중국", "중국"), ("미국", "미국")):
            if keyword in title:
                return topic
        return "국제금융"

    def kcif(self) -> list[dict]:
        rows = self.db.scalars(select(KcifReport).order_by(desc(KcifReport.report_date)).limit(3)).all()
        result = []
        for row in rows:
            summary = re.sub(r"\s+", " ", row.extracted_text).strip()
            result.append({
                "id": row.report_no, "title": row.title, "summary": row.ai_summary or summary[:240],
                "topic": row.ai_topic or self._kcif_topic(row.title), "source_url": row.source_url,
                "as_of": aware(row.ai_summarized_at or row.collected_at),
            })
        return result

    def research(self) -> list[dict]:
        rows = self.db.scalars(select(ResearchReport).order_by(
            desc(ResearchReport.published_on), desc(ResearchReport.id),
        ).limit(12)).all()
        return [{
            "id": row.id, "category": row.category, "title": row.title, "broker": row.broker,
            "analyst": row.analyst, "published_on": row.published_on, "stock_code": row.stock_code,
            "stock_name": row.stock_name, "source_url": row.source_url,
        } for row in rows]

    def freshness(self, now: datetime) -> list[dict]:
        specs = (
            ("market", "시장 데이터", MarketQuote.collected_at, timedelta(minutes=30)),
            ("news", "뉴스·이슈", NewsArticle.collected_at, timedelta(hours=6)),
            ("disclosure", "공시", Disclosure.collected_at, timedelta(hours=36)),
            ("calendar", "주요 일정", EconomicEvent.collected_at, timedelta(hours=36)),
            ("kcif", "KCIF", KcifReport.collected_at, timedelta(hours=36)),
        )
        result = []
        for dataset, label, column, threshold in specs:
            as_of = aware(self.db.scalar(select(func.max(column))))
            if as_of is not None:
                result.append({"dataset": dataset, "label": label, "as_of": as_of, "stale": now - as_of > threshold})
        return result
