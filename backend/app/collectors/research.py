import re
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://consensus.hankyung.com"
LIST_URL = f"{BASE_URL}/analysis/list"
STOCK_PATTERN = re.compile(r"(?P<name>[^\s\[(]{1,40})\s*\((?P<code>\d{6})\)")


@dataclass(frozen=True)
class ResearchReportPayload:
    source: str
    source_report_id: str
    category: str
    title: str
    broker: str
    analyst: str | None
    published_on: date
    stock_code: str | None
    stock_name: str | None
    opinion: str | None
    target_price: int | None
    previous_target_price: int | None
    source_url: str


def parse_reports(html: str) -> list[ResearchReportPayload]:
    soup = BeautifulSoup(html, "html.parser")
    reports: list[ResearchReportPayload] = []
    for row in soup.select(".table_style01 tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 6:
            continue
        link = cells[2].find("a", href=re.compile(r"/analysis/downpdf\?report_idx="))
        if link is None:
            continue
        href = link.get("href", "")
        report_id = parse_qs(urlparse(href).query).get("report_idx", [""])[0]
        title = link.get_text(" ", strip=True)
        stock_match = STOCK_PATTERN.search(title)
        try:
            published_on = date.fromisoformat(cells[0].get_text(strip=True))
        except ValueError:
            continue
        if not report_id or not title:
            continue
        reports.append(ResearchReportPayload(
            source="hankyung_consensus",
            source_report_id=report_id,
            category=cells[1].get_text(" ", strip=True),
            title=title,
            broker=cells[4].get_text(" ", strip=True),
            analyst=cells[3].get_text(" ", strip=True) or None,
            published_on=published_on,
            stock_code=stock_match.group("code") if stock_match else None,
            stock_name=stock_match.group("name").strip("[]") if stock_match else None,
            opinion=None,
            target_price=None,
            previous_target_price=None,
            source_url=urljoin(BASE_URL, href),
        ))
    return reports


class ResearchCollector:
    async def collect(self, page_size: int = 80, max_pages: int = 5) -> list[ResearchReportPayload]:
        headers = {"User-Agent": "stock-hanaro/1.0 (research metadata index)", "Accept-Language": "ko-KR,ko;q=0.9"}
        today = date.today()
        reports: list[ResearchReportPayload] = []
        page_size = min(max(page_size, 20), 80)
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
            for page in range(1, min(max(max_pages, 1), 5) + 1):
                response = await client.get(LIST_URL, params={
                    "sdate": (today - timedelta(days=30)).isoformat(), "edate": today.isoformat(),
                    "pagenum": page_size, "now_page": page,
                })
                response.raise_for_status()
                if not response.charset_encoding:
                    response.encoding = response.apparent_encoding
                page_reports = parse_reports(response.text)
                reports.extend(page_reports)
                if len(page_reports) < page_size:
                    break
        return list({report.source_report_id: report for report in reports}.values())


research_collector = ResearchCollector()
