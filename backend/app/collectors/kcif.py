import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from app.core.config import settings


KCIF_BASE_URL = "https://www.kcif.or.kr"
KCIF_LIST_URL = f"{KCIF_BASE_URL}/annual/newsflashList"


@dataclass(frozen=True)
class KcifListItem:
    report_no: str
    report_date: date
    title: str
    author: str | None
    file_name: str
    download_token: str
    source_url: str


@dataclass(frozen=True)
class KcifReportPayload:
    report_no: str
    report_date: date
    title: str
    author: str | None
    file_name: str
    file_hash: str
    source_url: str
    extracted_text: str


def parse_kcif_list(html: str) -> list[KcifListItem]:
    soup = BeautifulSoup(html, "lxml")
    items: list[KcifListItem] = []
    for anchor in soup.find_all("a", href=lambda value: value and "/annual/reportView" in value):
        container = anchor.find_parent("li")
        if container is None:
            continue
        href = anchor.get("href", "")
        report_no = parse_qs(urlparse(href).query).get("rpt_no", [""])[0]
        download = container.find(attrs={"onclick": re.compile(r"reportdownload\(", re.I)})
        file_anchor = container.find("a", title=re.compile(r"\.pdf$", re.I))
        date_match = re.search(r"(20\d{2}\.\d{2}\.\d{2})", container.get_text(" ", strip=True))
        if not report_no or download is None or file_anchor is None or not date_match:
            continue
        token_match = re.search(r"reportdownload\('([^']+)'\)", download.get("onclick", ""), re.I)
        if not token_match:
            continue
        title = anchor.get_text(" ", strip=True)
        author_date_text = container.get_text(" ", strip=True)
        author_match = re.search(rf"{re.escape(title)}\s+(.*?)\s+{re.escape(date_match.group(1))}", author_date_text)
        items.append(KcifListItem(
            report_no=report_no, report_date=datetime.strptime(date_match.group(1), "%Y.%m.%d").date(),
            title=title, author=author_match.group(1).strip() if author_match else None,
            file_name=file_anchor.get("title", "report.pdf"), download_token=token_match.group(1),
            source_url=urljoin(KCIF_BASE_URL, href),
        ))
    unique = {item.report_no: item for item in items}
    return list(unique.values())


def extract_pdf_text(content: bytes) -> str:
    if not content.startswith(b"%PDF"):
        raise RuntimeError("KCIF download did not return a PDF")
    reader = PdfReader(io.BytesIO(content))
    text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    if not text:
        raise RuntimeError("KCIF PDF contains no extractable text")
    return text


class KcifCollector:
    async def collect(self, business_date: date) -> KcifReportPayload:
        headers = {"User-Agent": settings.news_user_agent, "Referer": KCIF_LIST_URL}
        async with httpx.AsyncClient(
            base_url=KCIF_BASE_URL, timeout=30, follow_redirects=True, headers=headers
        ) as client:
            list_response = await client.get("/annual/newsflashList")
            list_response.raise_for_status()
            matches = [item for item in parse_kcif_list(list_response.text) if item.report_date == business_date]
            if not matches:
                raise RuntimeError(f"KCIF report not published for {business_date.isoformat()}")
            item = matches[0]
            auth_response = await client.post("/comm/AuthCheck", data={
                "type": "FILE", "fno": item.download_token, "logType": "D", "lang": "KR",
            })
            auth_response.raise_for_status()
            if auth_response.json().get("auth_yn") != "Y":
                raise RuntimeError("KCIF report is not publicly downloadable")
            file_response = await client.get(
                "/common/file/reportFileDownload", params={"atch_no": unquote(item.download_token), "lang": "KR"}
            )
            file_response.raise_for_status()
        content = file_response.content
        return KcifReportPayload(
            report_no=item.report_no, report_date=item.report_date, title=item.title, author=item.author,
            file_name=item.file_name, file_hash=hashlib.sha256(content).hexdigest(), source_url=item.source_url,
            extracted_text=extract_pdf_text(content),
        )
