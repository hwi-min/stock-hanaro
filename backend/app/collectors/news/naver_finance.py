import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.collectors.news.normalizer import NormalizedNewsArticle, normalize_article
from app.core.config import settings


NEWS_LIST_URL = "https://finance.naver.com/news/news_list.naver"


class NaverFinanceNewsCollector:
    source = "naver_finance"

    async def collect(self, limit: int | None = None) -> list[NormalizedNewsArticle]:
        headers = {"User-Agent": settings.news_user_agent, "Accept-Language": "ko-KR,ko;q=0.9"}
        params = {"mode": "LSS2D", "section0": "101", "section1": "258"}
        async with httpx.AsyncClient(
            timeout=settings.news_request_timeout_seconds, headers=headers, follow_redirects=True
        ) as client:
            response = await client.get(NEWS_LIST_URL, params=params)
            response.raise_for_status()
        return self.parse(response.text, limit or settings.news_collect_limit)

    def parse(self, html: str, limit: int = 40) -> list[NormalizedNewsArticle]:
        soup = BeautifulSoup(html, "lxml")
        articles: list[NormalizedNewsArticle] = []
        for item in soup.select("ul.realtimeNewsList li"):
            subjects = item.select("dd.articleSubject a")
            summaries = item.select("dd.articleSummary")
            for index, anchor in enumerate(subjects):
                if len(articles) >= limit:
                    return articles
                title = anchor.get("title") or anchor.get_text(" ", strip=True)
                href = anchor.get("href", "")
                match = re.search(r"article_id=(\d+)&office_id=(\d+)", href)
                if match:
                    article_id, office_id = match.groups()
                    url = f"https://n.news.naver.com/mnews/article/{office_id}/{article_id}"
                    source_article_id = f"{office_id}:{article_id}"
                elif href:
                    url = f"https://finance.naver.com{href}" if href.startswith("/") else href
                    source_article_id = None
                else:
                    continue
                summary = publisher = None
                published_at = None
                if index < len(summaries):
                    summary_node = summaries[index]
                    publisher_node = summary_node.select_one("span.press")
                    date_node = summary_node.select_one("span.wdate")
                    publisher = publisher_node.get_text(" ", strip=True) if publisher_node else None
                    published_at = self._parse_datetime(date_node.get_text(strip=True)) if date_node else None
                    for node in summary_node.select("span"):
                        node.extract()
                    summary = summary_node.get_text(" ", strip=True)[:1000]
                try:
                    articles.append(normalize_article(
                        source=self.source, title=title, url=url, summary=summary, publisher=publisher,
                        published_at=published_at, source_article_id=source_article_id,
                    ))
                except ValueError:
                    continue
        return articles

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        for pattern in ("%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M"):
            try:
                return datetime.strptime(value.strip(), pattern)
            except ValueError:
                continue
        return None
