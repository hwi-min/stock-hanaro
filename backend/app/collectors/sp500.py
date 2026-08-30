import asyncio
import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import httpx
from bs4 import BeautifulSoup


IVV_HOLDINGS_URL = "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/latest-holdings.csv"
SP500_TAXONOMY_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

KIS_CLASS_SHARE_SYMBOLS = {
    "BFB": "BF/B",
    "BRKB": "BRK/B",
}


@dataclass(frozen=True)
class Sp500ConstituentPayload:
    symbol: str
    kis_symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
    index_weight: Decimal
    source_date: date


def _decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "").replace("%", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"invalid IVV weight: {value!r}") from exc


def _exchange(value: str) -> str:
    normalized = value.upper()
    if "NASDAQ" in normalized:
        return "NAS"
    if "NEW YORK" in normalized or normalized == "NYSE":
        return "NYS"
    return "AMS"


def normalize_kis_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    return KIS_CLASS_SHARE_SYMBOLS.get(normalized, normalized.replace(".", "/"))


def kis_symbol_candidates(symbol: str, stored_kis_symbol: str) -> list[str]:
    candidates = [stored_kis_symbol, normalize_kis_symbol(symbol)]
    if any("/" in candidate for candidate in candidates):
        candidates.extend([symbol, symbol.replace(".", "-")])
    return list(dict.fromkeys(candidates))


class Sp500MasterCollector:
    async def collect(self) -> list[Sp500ConstituentPayload]:
        headers = {"User-Agent": "stock-hanaro/0.1 (S&P 500 close heatmap)"}
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
            holdings_response, taxonomy_response = await asyncio.gather(
                client.get(IVV_HOLDINGS_URL), client.get(SP500_TAXONOMY_URL)
            )
        holdings_response.raise_for_status()
        taxonomy_response.raise_for_status()
        taxonomy = self._parse_taxonomy(taxonomy_response.text)
        return self._parse_holdings(holdings_response.content.decode("utf-8-sig"), taxonomy)

    @staticmethod
    def _parse_taxonomy(html: str) -> dict[str, tuple[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="constituents")
        if table is None:
            raise RuntimeError("S&P 500 taxonomy table was not found")
        result: dict[str, tuple[str, str]] = {}
        for row in table.select("tbody tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue
            symbol = cells[0].get_text(" ", strip=True).replace(".", "-")
            result[symbol] = (cells[2].get_text(" ", strip=True), cells[3].get_text(" ", strip=True))
        return result

    @staticmethod
    def _parse_holdings(text: str, taxonomy: dict[str, tuple[str, str]]) -> list[Sp500ConstituentPayload]:
        lines = text.splitlines()
        header_index = next((index for index, line in enumerate(lines) if line.startswith("Ticker,")), None)
        if header_index is None:
            raise RuntimeError("IVV holdings header was not found")
        reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])))
        result: list[Sp500ConstituentPayload] = []
        fallback_date = datetime.utcnow().date()
        source_date = fallback_date
        if len(lines) > 1 and lines[1].startswith("Fund Holdings as of,"):
            raw_source_date = next(csv.reader([lines[1]]))[1]
            try:
                source_date = datetime.strptime(raw_source_date, "%b %d, %Y").date()
            except ValueError:
                pass
        for row in reader:
            symbol = (row.get("Ticker") or "").strip()
            asset_class = (row.get("Asset Class") or "").strip().lower()
            if not symbol or asset_class != "equity" or symbol in {"-", "USD"}:
                continue
            weight = _decimal(row.get("Weight (%)") or "0")
            if weight <= 0:
                continue
            taxonomy_key = symbol.replace(".", "-")
            sector, industry = taxonomy.get(taxonomy_key, ((row.get("Sector") or "Other").strip(), "Other"))
            result.append(Sp500ConstituentPayload(
                symbol=symbol, kis_symbol=normalize_kis_symbol(symbol), name=(row.get("Name") or symbol).strip(),
                exchange=_exchange(row.get("Exchange") or ""), sector=sector or "Other",
                industry=industry or "Other", index_weight=weight,
                source_date=source_date,
            ))
        if len(result) < 490:
            raise RuntimeError(f"IVV holdings returned only {len(result)} equities")
        return result


sp500_master_collector = Sp500MasterCollector()
