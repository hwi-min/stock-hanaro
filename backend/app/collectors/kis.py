import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class QuotePayload:
    provider: str
    market: str
    asset_type: str
    exchange: str | None
    symbol: str
    name: str | None
    sector: str | None
    industry: str | None
    currency: str | None
    price: Decimal
    change: Decimal | None
    change_pct: Decimal | None
    volume: Decimal | None
    market_cap: Decimal | None
    as_of: datetime


def decimal_or_none(value) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", "")) if value not in (None, "") else None
    except (InvalidOperation, ValueError):
        return None


class KISClient:
    def __init__(self):
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()

    async def get_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._token and self._token_expires_at and now < self._token_expires_at:
            return self._token
        async with self._token_lock:
            now = datetime.now(timezone.utc)
            if self._token and self._token_expires_at and now < self._token_expires_at:
                return self._token
            cached = self._load_cached_token(now)
            if cached:
                return cached
            if not settings.kis_app_key or not settings.kis_app_secret:
                raise RuntimeError("KIS_APP_KEY and KIS_APP_SECRET are required")
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{settings.kis_base_url}/oauth2/tokenP",
                    json={"grant_type": "client_credentials", "appkey": settings.kis_app_key, "appsecret": settings.kis_app_secret},
                )
                response.raise_for_status()
                data = response.json()
            self._token = data["access_token"]
            ttl = max(int(data.get("expires_in", 86400)) - 600, 60)
            self._token_expires_at = now + timedelta(seconds=ttl)
            self._save_cached_token(self._token, self._token_expires_at, now)
            return self._token

    @staticmethod
    def _environment() -> str:
        return "mock" if settings.kis_is_mock else "real"

    def _load_cached_token(self, now: datetime) -> str | None:
        from app.core.database import SessionLocal
        from app.models.kis_token import KisToken

        with SessionLocal() as db:
            row = db.get(KisToken, self._environment())
            if row is None:
                return None
            expires_at = row.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now + timedelta(minutes=5) >= expires_at:
                return None
            self._token = row.access_token
            self._token_expires_at = expires_at
            return self._token

    def _save_cached_token(self, token: str, expires_at: datetime, issued_at: datetime) -> None:
        from app.core.database import SessionLocal
        from app.models.kis_token import KisToken

        with SessionLocal() as db:
            row = db.get(KisToken, self._environment())
            if row is None:
                db.add(KisToken(
                    environment=self._environment(), access_token=token,
                    expires_at=expires_at, issued_at=issued_at,
                ))
            else:
                row.access_token = token
                row.expires_at = expires_at
                row.issued_at = issued_at
            db.commit()

    async def _get(self, path: str, tr_id: str, params: dict[str, str]) -> dict:
        token = await self.get_token()
        headers = {
            "authorization": f"Bearer {token}", "appkey": settings.kis_app_key,
            "appsecret": settings.kis_app_secret, "tr_id": tr_id, "custtype": "P",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{settings.kis_base_url}{path}", headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
        if data.get("rt_cd") not in (None, "0"):
            raise RuntimeError(f"KIS {tr_id}: {data.get('msg_cd')} {data.get('msg1')}")
        return data

    async def overseas_price(self, symbol: str, exchange: str = "NAS") -> QuotePayload:
        data = await self._get(
            "/uapi/overseas-price/v1/quotations/price", "HHDFS00000300",
            {"AUTH": "", "EXCD": exchange, "SYMB": symbol},
        )
        output = data.get("output", {})
        price = decimal_or_none(output.get("last"))
        if price is None:
            raise RuntimeError(f"KIS returned no price for {exchange}:{symbol}")
        return QuotePayload(
            provider="kis", market="us", asset_type="equity", exchange=exchange, symbol=symbol,
            name=output.get("name") or output.get("symb"), sector=None, industry=None, currency="USD", price=price,
            change=decimal_or_none(output.get("diff")), change_pct=decimal_or_none(output.get("rate")),
            volume=decimal_or_none(output.get("tvol")), market_cap=decimal_or_none(output.get("tomv")),
            as_of=datetime.now(timezone.utc),
        )

    async def overseas_price_detail(self, symbol: str, exchange: str, metadata: dict) -> QuotePayload:
        data = await self._get(
            "/uapi/overseas-price/v1/quotations/price-detail", "HHDFS76200200",
            {"AUTH": "", "EXCD": exchange, "SYMB": symbol},
        )
        output = data.get("output", {})
        price = decimal_or_none(output.get("last"))
        base = decimal_or_none(output.get("base"))
        if price is None:
            raise RuntimeError(f"KIS returned no detailed price for {exchange}:{symbol}")
        change = price - base if base is not None else decimal_or_none(output.get("diff"))
        change_pct = (change / base * 100) if change is not None and base else decimal_or_none(output.get("rate"))
        return QuotePayload(
            provider="kis", market="us", asset_type="equity", exchange=exchange, symbol=symbol,
            name=metadata.get("name") or output.get("name"), sector=metadata.get("sector"),
            industry=metadata.get("industry"), currency=output.get("curr") or "USD", price=price,
            change=change, change_pct=change_pct, volume=decimal_or_none(output.get("tvol")),
            market_cap=decimal_or_none(output.get("tomv")), as_of=datetime.now(timezone.utc),
        )

    async def domestic_index(self, symbol: str, code: str, name: str) -> QuotePayload:
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-index-price", "FHPUP02100000",
            {"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": code},
        )
        output = data.get("output", {})
        price = decimal_or_none(output.get("bstp_nmix_prpr"))
        if price is None:
            raise RuntimeError(f"KIS returned no domestic index price for {symbol}")
        return QuotePayload(
            provider="kis", market="kr", asset_type="index", exchange="KRX", symbol=symbol, name=name,
            sector=None, industry=None, currency="KRW", price=price,
            change=decimal_or_none(output.get("bstp_nmix_prdy_vrss")),
            change_pct=decimal_or_none(output.get("bstp_nmix_prdy_ctrt")),
            volume=decimal_or_none(output.get("acml_vol")), market_cap=None, as_of=datetime.now(timezone.utc),
        )

    async def domestic_price(self, symbol: str) -> dict:
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price", "FHKST01010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
        )
        output = data.get("output", {})
        price = decimal_or_none(output.get("stck_prpr"))
        if price is None or price <= 0:
            raise RuntimeError(f"KIS returned no domestic price for {symbol}")
        return {
            "price": price, "change": decimal_or_none(output.get("prdy_vrss")),
            "change_pct": decimal_or_none(output.get("prdy_ctrt")),
            "volume": decimal_or_none(output.get("acml_vol")),
            "market_cap": decimal_or_none(output.get("hts_avls")),
            "per": decimal_or_none(output.get("per")), "pbr": decimal_or_none(output.get("pbr")),
            "foreign_ownership_pct": decimal_or_none(output.get("hts_frgn_ehrt")),
            "high_52w": decimal_or_none(output.get("d250_hgpr")),
            "low_52w": decimal_or_none(output.get("d250_lwpr")),
            "name": output.get("hts_kor_isnm"), "as_of": datetime.now(timezone.utc),
        }

    async def domestic_chart(self, symbol: str, period: str = "D", days: int = 100) -> list[dict]:
        end = date.today()
        lookback_days = {"D": max(days * 2, 180), "W": max(days * 10, 1095), "M": max(days * 40, 3650)}[period]
        start = end - timedelta(days=lookback_days)
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", "FHKST03010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol,
             "FID_INPUT_DATE_1": start.strftime("%Y%m%d"), "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
             "FID_PERIOD_DIV_CODE": period, "FID_ORG_ADJ_PRC": "0"},
        )
        rows = data.get("output2", [])[:days]
        return list(reversed([{
            "time": row.get("stck_bsop_date"), "open": decimal_or_none(row.get("stck_oprc")),
            "high": decimal_or_none(row.get("stck_hgpr")), "low": decimal_or_none(row.get("stck_lwpr")),
            "close": decimal_or_none(row.get("stck_clpr")), "volume": decimal_or_none(row.get("acml_vol")),
        } for row in rows if decimal_or_none(row.get("stck_clpr")) is not None]))

    async def domestic_daily_chart(self, symbol: str, days: int = 100) -> list[dict]:
        return await self.domestic_chart(symbol, "D", days)

    async def domestic_minute_chart(self, symbol: str) -> list[dict]:
        data = await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice", "FHKST03010200",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol, "FID_INPUT_HOUR_1": "153000",
             "FID_PW_DATA_INCU_YN": "Y", "FID_ETC_CLS_CODE": ""},
        )
        return list(reversed([{
            "time": row.get("stck_cntg_hour"), "open": decimal_or_none(row.get("stck_oprc")),
            "high": decimal_or_none(row.get("stck_hgpr")), "low": decimal_or_none(row.get("stck_lwpr")),
            "close": decimal_or_none(row.get("stck_prpr")), "volume": decimal_or_none(row.get("cntg_vol")),
        } for row in data.get("output2", []) if decimal_or_none(row.get("stck_prpr")) is not None]))

    async def overseas_daily_chart(self, symbol: str, exchange: str) -> list[dict]:
        data = await self._get(
            "/uapi/overseas-price/v1/quotations/dailyprice", "HHDFS76240000",
            {"AUTH": "", "EXCD": exchange, "SYMB": symbol, "GUBN": "0", "BYMD": "", "MODP": "1"},
        )
        return list(reversed([{
            "time": row.get("xymd"), "open": decimal_or_none(row.get("open")),
            "high": decimal_or_none(row.get("high")), "low": decimal_or_none(row.get("low")),
            "close": decimal_or_none(row.get("clos")), "volume": decimal_or_none(row.get("tvol")),
        } for row in data.get("output2", []) if decimal_or_none(row.get("clos")) is not None]))
    async def overseas_index(self, symbol: str, code: str, name: str) -> QuotePayload:
        data = await self._get(
            "/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice", "FHKST03030200",
            {"FID_COND_MRKT_DIV_CODE": "N", "FID_INPUT_ISCD": code,
             "FID_HOUR_CLS_CODE": "0", "FID_PW_DATA_INCU_YN": "Y"},
        )
        output = data.get("output1", {})
        price = decimal_or_none(output.get("ovrs_nmix_prpr"))
        if price is None or price <= 0:
            raise RuntimeError(f"KIS returned no overseas index price for {symbol}")
        return QuotePayload(
            provider="kis", market="us", asset_type="index", exchange=None, symbol=symbol, name=name,
            sector=None, industry=None, currency="USD", price=price,
            change=decimal_or_none(output.get("ovrs_nmix_prdy_vrss")),
            change_pct=decimal_or_none(output.get("prdy_ctrt")),
            volume=decimal_or_none(output.get("acml_vol")), market_cap=None, as_of=datetime.now(timezone.utc),
        )

    async def usd_krw(self) -> QuotePayload:
        end = date.today()
        data = await self._get(
            "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice", "FHKST03030100",
            {"FID_COND_MRKT_DIV_CODE": "X", "FID_INPUT_ISCD": "FX@KRWKFTC",
             "FID_INPUT_DATE_1": (end - timedelta(days=10)).strftime("%Y%m%d"),
             "FID_INPUT_DATE_2": end.strftime("%Y%m%d"), "FID_PERIOD_DIV_CODE": "D"},
        )
        output = data.get("output1", {})
        price = decimal_or_none(output.get("ovrs_nmix_prpr"))
        if price is None or price <= 0:
            raise RuntimeError("KIS returned no USD/KRW price")
        return QuotePayload(
            provider="kis", market="kr", asset_type="fx", exchange=None, symbol="USDKRW", name="원/달러",
            sector=None, industry=None, currency="KRW", price=price,
            change=decimal_or_none(output.get("ovrs_nmix_prdy_vrss")),
            change_pct=decimal_or_none(output.get("prdy_ctrt")), volume=None, market_cap=None,
            as_of=datetime.now(timezone.utc),
        )

    @staticmethod
    def gold_contract(reference: date | None = None) -> str:
        reference = reference or date.today()
        month_codes = ((2, "G"), (4, "J"), (6, "M"), (8, "Q"), (10, "V"), (12, "Z"))
        year = reference.year
        for month, code in month_codes:
            if month > reference.month:
                return f"1OZ{code}{year % 100:02d}"
        return f"1OZG{(year + 1) % 100:02d}"

    async def gold(self) -> QuotePayload:
        contract = self.gold_contract()
        data = await self._get(
            "/uapi/overseas-futureoption/v1/quotations/inquire-price", "HHDFC55010000", {"SRS_CD": contract},
        )
        output = data.get("output1", {})
        # 1oz Gold master uses two implied decimal places (e.g. 402325 -> 4023.25 USD/oz).
        price_raw = decimal_or_none(str(output.get("last_price", "")).strip())
        change_raw = decimal_or_none(str(output.get("prev_diff_price", "")).strip())
        if price_raw is None or price_raw <= 0:
            raise RuntimeError(f"KIS returned no Gold price for {contract}")
        sign = -1 if output.get("prev_diff_flag") in {"4", "5"} else 1
        return QuotePayload(
            provider="kis", market="global", asset_type="commodity", exchange=output.get("exch_cd") or "CME",
            symbol="GOLD", name="Gold", sector=None, industry=None, currency=output.get("crc_cd") or "USD",
            price=price_raw / 100, change=(change_raw / 100 * sign) if change_raw is not None else None,
            change_pct=decimal_or_none(str(output.get("prev_diff_rate", "")).strip()) * sign
            if decimal_or_none(str(output.get("prev_diff_rate", "")).strip()) is not None else None,
            volume=decimal_or_none(output.get("vol")), market_cap=None, as_of=datetime.now(timezone.utc),
        )

    async def korea_treasury_3y(self) -> QuotePayload:
        if not settings.bok_ecos_api_key:
            raise RuntimeError("BOK_ECOS_API_KEY is required for Korea Treasury 3Y")
        end = date.today()
        start = end - timedelta(days=10 if settings.bok_ecos_api_key == "sample" else 14)
        row_limit = 10 if settings.bok_ecos_api_key == "sample" else 100
        url = (
            f"https://ecos.bok.or.kr/api/StatisticSearch/{settings.bok_ecos_api_key}/json/kr/1/{row_limit}/"
            f"817Y002/D/{start:%Y%m%d}/{end:%Y%m%d}/010200000"
        )
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        rows = data.get("StatisticSearch", {}).get("row", [])
        if not rows:
            error = data.get("RESULT", {}).get("MESSAGE", "no rows")
            raise RuntimeError(f"BOK ECOS returned no Korea Treasury 3Y data: {error}")
        rows.sort(key=lambda row: row["TIME"])
        latest = rows[-1]
        previous = rows[-2] if len(rows) > 1 else None
        price = decimal_or_none(latest.get("DATA_VALUE"))
        previous_price = decimal_or_none(previous.get("DATA_VALUE")) if previous else None
        if price is None:
            raise RuntimeError("BOK ECOS returned an invalid Korea Treasury 3Y value")
        change = price - previous_price if previous_price is not None else None
        return QuotePayload(
            provider="bok_ecos", market="kr", asset_type="yield", exchange=None, symbol="KTB3Y",
            name="국고채 3년", sector=None, industry=None, currency="PCT", price=price, change=change,
            change_pct=(change / previous_price * 100) if change is not None and previous_price else None,
            volume=None, market_cap=None,
            as_of=datetime.strptime(latest["TIME"], "%Y%m%d").replace(tzinfo=timezone.utc),
        )

    async def collect_us_close_snapshot(self) -> tuple[list[QuotePayload], list[str]]:
        quotes, errors = [], []
        for symbol, metadata in US_HEATMAP_UNIVERSE.items():
            try:
                quotes.append(await self.overseas_price_detail(symbol, metadata["exchange"], metadata))
            except Exception as exc:
                errors.append(f"{symbol}: {exc}")
            await asyncio.sleep(settings.kis_request_interval_seconds)
        for symbol, code, name in OVERSEAS_INDICES:
            try:
                quotes.append(await self.overseas_index(symbol, code, name))
            except Exception as exc:
                errors.append(f"{symbol}: {exc}")
            await asyncio.sleep(settings.kis_request_interval_seconds)
        try:
            quotes.append(await self.gold())
        except Exception as exc:
            errors.append(f"GOLD: {exc}")
        return quotes, errors

    async def collect_kr_snapshot(self) -> tuple[list[QuotePayload], list[str]]:
        quotes, errors = [], []
        for symbol, code, name in DOMESTIC_INDICES:
            try:
                quotes.append(await self.domestic_index(symbol, code, name))
            except Exception as exc:
                errors.append(f"{symbol}: {exc}")
            await asyncio.sleep(settings.kis_request_interval_seconds)
        for symbol, collector in (("USDKRW", self.usd_krw), ("KTB3Y", self.korea_treasury_3y)):
            try:
                quotes.append(await collector())
            except Exception as exc:
                errors.append(f"{symbol}: {exc}")
            await asyncio.sleep(settings.kis_request_interval_seconds)
        return quotes, errors

    async def collect_market_snapshot(self) -> tuple[list[QuotePayload], list[str]]:
        """Backward-compatible manual collection of both close and domestic snapshots."""
        us_quotes, us_errors = await self.collect_us_close_snapshot()
        kr_quotes, kr_errors = await self.collect_kr_snapshot()
        return us_quotes + kr_quotes, us_errors + kr_errors


US_HEATMAP_UNIVERSE = {
    "AAPL": {"name": "Apple", "exchange": "NAS", "sector": "기술", "industry": "소비자 전자제품"},
    "MSFT": {"name": "Microsoft", "exchange": "NAS", "sector": "기술", "industry": "소프트웨어"},
    "NVDA": {"name": "NVIDIA", "exchange": "NAS", "sector": "기술", "industry": "반도체"},
    "GOOGL": {"name": "Alphabet", "exchange": "NAS", "sector": "커뮤니케이션 서비스", "industry": "인터넷 콘텐츠"},
    "META": {"name": "Meta", "exchange": "NAS", "sector": "커뮤니케이션 서비스", "industry": "인터넷 콘텐츠"},
    "AMZN": {"name": "Amazon", "exchange": "NAS", "sector": "경기소비재", "industry": "인터넷 유통"},
    "TSLA": {"name": "Tesla", "exchange": "NAS", "sector": "경기소비재", "industry": "자동차"},
    "AVGO": {"name": "Broadcom", "exchange": "NAS", "sector": "기술", "industry": "반도체"},
    "AMD": {"name": "AMD", "exchange": "NAS", "sector": "기술", "industry": "반도체"},
    "COST": {"name": "Costco", "exchange": "NAS", "sector": "필수소비재", "industry": "할인점"},
    "JPM": {"name": "JPMorgan", "exchange": "NYS", "sector": "금융", "industry": "은행"},
    "V": {"name": "Visa", "exchange": "NYS", "sector": "금융", "industry": "신용서비스"},
    "LLY": {"name": "Eli Lilly", "exchange": "NYS", "sector": "헬스케어", "industry": "제약"},
    "UNH": {"name": "UnitedHealth", "exchange": "NYS", "sector": "헬스케어", "industry": "건강보험"},
    "XOM": {"name": "Exxon Mobil", "exchange": "NYS", "sector": "에너지", "industry": "석유·가스"},
    "CVX": {"name": "Chevron", "exchange": "NYS", "sector": "에너지", "industry": "석유·가스"},
    "PG": {"name": "Procter & Gamble", "exchange": "NYS", "sector": "필수소비재", "industry": "생활용품"},
    "HD": {"name": "Home Depot", "exchange": "NYS", "sector": "경기소비재", "industry": "주택개량 유통"},
    "GE": {"name": "GE Aerospace", "exchange": "NYS", "sector": "산업재", "industry": "항공우주"},
    "CAT": {"name": "Caterpillar", "exchange": "NYS", "sector": "산업재", "industry": "중장비"},
}

DOMESTIC_INDICES = (("KOSPI", "0001", "코스피"), ("KOSDAQ", "1001", "코스닥"), ("KOSPI200", "2001", "코스피 200"))
OVERSEAS_INDICES = (("SPX", "SPX", "S&P 500"), ("NASDAQ", "COMP", "NASDAQ"), ("DOW30", ".DJI", "Dow 30"), ("RUSSELL2000", "RUT", "Russell 2000"), ("VIX", "VIX", "VIX"))

kis_client = KISClient()
