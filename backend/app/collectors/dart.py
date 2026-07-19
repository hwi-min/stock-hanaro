from dataclasses import dataclass
from datetime import date, datetime

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class DisclosurePayload:
    receipt_no: str
    corp_code: str
    corp_name: str
    stock_code: str | None
    title: str
    receipt_date: date
    report_type: str | None
    submitter: str | None
    remarks: str | None
    source_url: str
    corp_cls: str
    category: str
    importance: str
    is_correction: bool


REPORT_CATEGORIES = {
    "A": "정기공시", "B": "주요사항", "C": "발행공시", "D": "지분공시", "E": "기타공시",
    "F": "외부감사", "G": "펀드공시", "H": "자산유동화", "I": "거래소공시", "J": "공정위공시",
}

HIGH_IMPORTANCE_KEYWORDS = (
    "부도", "회생절차", "파산", "영업정지", "상장폐지", "횡령", "배임", "유상증자", "무상증자", "감자",
    "합병", "분할", "주식교환", "주식이전", "공개매수", "최대주주변경", "최대주주 변경", "전환사채",
    "신주인수권부사채", "교환사채", "자기주식취득", "자기주식처분", "자기주식 취득", "자기주식 처분",
    "단일판매ㆍ공급계약", "단일판매·공급계약", "소송등의제기", "소송 등의 제기",
    "거래처와의거래중단", "주권매매거래정지", "관리종목지정", "불성실공시법인지정",
)

MEDIUM_IMPORTANCE_KEYWORDS = (
    "사업보고서", "반기보고서", "분기보고서", "감사보고서", "주식등의대량보유", "임원ㆍ주요주주",
    "현금ㆍ현물배당", "현금·현물배당", "타법인주식", "시설투자", "영업양수", "영업양도",
)


class DartClient:
    async def collect(self, business_date: date) -> list[DisclosurePayload]:
        if not settings.dart_api_key:
            raise RuntimeError("DART_API_KEY is required")
        disclosures: list[DisclosurePayload] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for corp_cls in ("Y", "K", "N"):
                for report_type in ("A", "B", "C", "D", "E", "F", "I", "J"):
                    disclosures.extend(await self._collect_market(client, business_date, corp_cls, report_type))
        return disclosures

    async def _collect_market(
        self, client: httpx.AsyncClient, business_date: date, corp_cls: str, report_type: str,
    ) -> list[DisclosurePayload]:
        value = business_date.strftime("%Y%m%d")
        items: list[DisclosurePayload] = []
        page_no = 1
        total_page = 0
        while page_no <= settings.dart_max_pages_per_market:
            params = {
                "crtfc_key": settings.dart_api_key, "bgn_de": value, "end_de": value,
                "corp_cls": corp_cls, "pblntf_ty": report_type, "sort": "date", "sort_mth": "desc",
                "page_no": str(page_no), "page_count": str(settings.dart_page_count),
            }
            response = await client.get("https://opendart.fss.or.kr/api/list.json", params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "013":
                break
            if data.get("status") != "000":
                raise RuntimeError(f"DART {data.get('status')}: {data.get('message')}")
            items.extend(self._normalize({**row, "pblntf_ty": report_type}) for row in data.get("list", []))
            total_page = int(data.get("total_page") or 1)
            if page_no >= total_page:
                break
            page_no += 1
        if total_page > settings.dart_max_pages_per_market:
            raise RuntimeError(f"DART pagination limit exceeded for corp_cls={corp_cls}, pblntf_ty={report_type}")
        return items

    @staticmethod
    def _importance(title: str, report_type: str | None) -> str:
        compact = title.replace(" ", "")
        if any(keyword.replace(" ", "") in compact for keyword in HIGH_IMPORTANCE_KEYWORDS):
            return "high"
        if report_type in {"B", "C", "I"} or any(
            keyword.replace(" ", "") in compact for keyword in MEDIUM_IMPORTANCE_KEYWORDS
        ):
            return "medium"
        return "low"

    @staticmethod
    def _normalize(row: dict) -> DisclosurePayload:
        receipt_no = row["rcept_no"]
        title = row["report_nm"]
        report_type = row.get("pblntf_ty")
        return DisclosurePayload(
            receipt_no=receipt_no, corp_code=row["corp_code"], corp_name=row["corp_name"],
            stock_code=(row.get("stock_code") or None), title=title,
            receipt_date=datetime.strptime(row["rcept_dt"], "%Y%m%d").date(),
            report_type=report_type, submitter=row.get("flr_nm"), remarks=row.get("rm"),
            source_url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={receipt_no}",
            corp_cls=row.get("corp_cls") or "E", category=REPORT_CATEGORIES.get(report_type, "기타공시"),
            importance=DartClient._importance(title, report_type),
            is_correction=title.startswith("[기재정정]") or title.startswith("[첨부정정]"),
        )
