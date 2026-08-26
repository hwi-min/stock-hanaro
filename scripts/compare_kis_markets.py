"""Compare KRX, NXT, and unified KIS quotes without printing credentials."""

import asyncio
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.collectors.kis import kis_client  # noqa: E402


async def main(symbol: str) -> None:
    for market in ("J", "NX", "UN"):
        try:
            data = await kis_client._get(
                "/uapi/domestic-stock/v1/quotations/inquire-price-2",
                "FHPST01010000",
                {"FID_COND_MRKT_DIV_CODE": market, "FID_INPUT_ISCD": symbol},
            )
            output = data.get("output", {})
            fields = (
                "stck_prpr", "prdy_vrss", "prdy_ctrt", "acml_vol", "hts_kor_isnm",
                "hts_avls", "per", "pbr", "hts_frgn_ehrt", "d250_hgpr", "d250_lwpr",
            )
            print(market, {field: output.get(field) for field in fields})
        except Exception as exc:
            print(market, type(exc).__name__, str(exc)[:160])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "005930"))
