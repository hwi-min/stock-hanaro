import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ValuationMetrics:
    psr: float | None = None
    pcr: float | None = None
    ev_ebitda: float | None = None
    basis: str | None = None
    source: str | None = None


def _metric(text: str, label: str) -> float | None:
    match = re.search(rf"{re.escape(label)}\s+(-?[\d,.]+)", text, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_theinvest(html: str) -> tuple[float | None, float | None]:
    text = " ".join(BeautifulSoup(html, "lxml").stripped_strings)
    return _metric(text, "PSR"), _metric(text, "PCR")


def parse_wisereport(html: str) -> float | None:
    text = " ".join(BeautifulSoup(html, "lxml").stripped_strings)
    return _metric(text, "EV/EBITDA")


class ValuationCollector:
    def __init__(self, ttl: timedelta = timedelta(hours=6)):
        self._ttl = ttl
        self._cache: dict[str, tuple[datetime, ValuationMetrics]] = {}
        self._lock = asyncio.Lock()

    async def get(self, symbol: str) -> ValuationMetrics:
        now = datetime.now(timezone.utc)
        cached = self._cache.get(symbol)
        if cached and now < cached[0]:
            return cached[1]

        async with self._lock:
            cached = self._cache.get(symbol)
            if cached and now < cached[0]:
                return cached[1]
            value = await self._fetch(symbol)
            self._cache[symbol] = (now + self._ttl, value)
            return value

    async def _fetch(self, symbol: str) -> ValuationMetrics:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; StockHanaro/0.1)"}
        urls = (
            f"https://theinvest.co.kr/compinfo.php?cd={symbol}",
            f"https://comp.wisereport.co.kr/company/c1010001.aspx?cmp_cd={symbol}",
        )
        async with httpx.AsyncClient(timeout=8, headers=headers, follow_redirects=True) as client:
            results = await asyncio.gather(*(client.get(url) for url in urls), return_exceptions=True)

        psr = pcr = ev_ebitda = None
        sources: list[str] = []
        if isinstance(results[0], httpx.Response) and results[0].is_success:
            psr, pcr = parse_theinvest(results[0].text)
            if psr is not None or pcr is not None:
                sources.append("더인베스트")
        if isinstance(results[1], httpx.Response) and results[1].is_success:
            ev_ebitda = parse_wisereport(results[1].text)
            if ev_ebitda is not None:
                sources.append("WiseReport")
        return ValuationMetrics(
            psr=psr,
            pcr=pcr,
            ev_ebitda=ev_ebitda,
            basis="최근 확정실적(TTM/연간)" if sources else None,
            source=" · ".join(sources) or None,
        )


valuation_collector = ValuationCollector()
