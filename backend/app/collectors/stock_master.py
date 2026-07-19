import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass(frozen=True)
class StockMasterPayload:
    symbol: str
    isin: str | None
    name: str
    market: str
    product_type: str
    active: bool
    collected_at: datetime
    updated_at: datetime


MASTER_FILES = {
    "KOSPI": ("https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip", "kospi_code.mst", 228),
    "KOSDAQ": ("https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip", "kosdaq_code.mst", 222),
}


class KISStockMasterCollector:
    @staticmethod
    def parse(content: bytes, *, market: str, tail_width: int) -> list[StockMasterPayload]:
        now = datetime.now(timezone.utc)
        rows: list[StockMasterPayload] = []
        for raw in content.decode("cp949", errors="replace").splitlines():
            if len(raw) <= tail_width:
                continue
            prefix, tail = raw[:-tail_width], raw[-tail_width:]
            symbol, isin, name = prefix[:9].strip(), prefix[9:21].strip(), prefix[21:].strip()
            # KIS fixed-width rows place a padding space before the two-letter
            # group code (ST: listed stock, EF: ETF, FS: foreign stock, ...).
            product_type = tail.lstrip()[:2]
            if not re.fullmatch(r"\d{6}", symbol) or not name or product_type != "ST":
                continue
            rows.append(StockMasterPayload(
                symbol=symbol, isin=isin or None, name=name, market=market, product_type=product_type,
                active=True, collected_at=now, updated_at=now,
            ))
        return rows

    async def collect(self) -> list[StockMasterPayload]:
        result: list[StockMasterPayload] = []
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for market, (url, filename, tail_width) in MASTER_FILES.items():
                response = await client.get(url)
                response.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    content = archive.read(filename)
                result.extend(self.parse(content, market=market, tail_width=tail_width))
        if not result:
            raise RuntimeError("KIS stock master returned no common stocks")
        return result


stock_master_collector = KISStockMasterCollector()
