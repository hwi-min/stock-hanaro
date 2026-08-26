import asyncio
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.collectors.kis import KISClient
from app.models.sp500 import Sp500Constituent
from app.repositories.sp500 import Sp500Repository
from app.core.config import settings


class Sp500CloseService:
    def __init__(self, repository: Sp500Repository, client: KISClient):
        self.repository = repository
        self.client = client

    async def collect(self) -> tuple[list[dict], list[str]]:
        constituents = self.repository.active_constituents()
        if not constituents:
            raise RuntimeError("S&P 500 constituent master is empty; run collect-sp500-master first")
        requested_date = datetime.now(ZoneInfo("America/New_York")).date()
        benchmark = await self.client.overseas_regular_close("SPY", "AMS", requested_date)
        target_date = datetime.strptime(str(benchmark["time"]), "%Y%m%d").date()
        completed = self.repository.snapshot_symbols(target_date)
        pending = [item for item in constituents if item.symbol not in completed]
        snapshots: list[dict] = []
        errors: list[str] = []
        for constituent in pending:
            try:
                history, regular = await self._history(constituent, target_date)
                trading_date = datetime.strptime(str(regular["time"]), "%Y%m%d").date()
                if trading_date != target_date:
                    raise RuntimeError(f"latest bar is {trading_date}, expected {target_date}")
                target_index = next((index for index, row in enumerate(history) if str(row["time"]) == f"{target_date:%Y%m%d}"), None)
                if target_index is None or target_index < 1:
                    raise RuntimeError("previous daily close was not found")
                close = Decimal(regular["close"])
                previous_close = Decimal(history[target_index - 1]["close"])
                if close <= 0 or previous_close <= 0:
                    raise RuntimeError("invalid close price")
                volume = Decimal(regular["volume"]) if regular.get("volume") is not None else None
                prior_volumes = [Decimal(row["volume"]) for row in history[max(0, target_index - 20):target_index] if row.get("volume") is not None]
                average_volume = sum(prior_volumes, Decimal(0)) / len(prior_volumes) if prior_volumes else None
                snapshots.append({
                    "trading_date": target_date, "symbol": constituent.symbol, "close": close,
                    "previous_close": previous_close, "change_pct": (close / previous_close - 1) * 100,
                    "volume": volume, "average_volume_20d": average_volume,
                    "dollar_volume": close * volume if volume is not None else None,
                    "relative_volume": volume / average_volume if volume is not None and average_volume else None,
                    "index_weight": constituent.index_weight,
                })
            except Exception as exc:
                errors.append(f"{constituent.symbol}: {exc}")
            await asyncio.sleep(settings.kis_request_interval_seconds)
        return snapshots, errors

    async def _history(self, constituent: Sp500Constituent, target_date) -> tuple[list[dict], dict]:
        candidates = [constituent.kis_symbol]
        if "/" in constituent.kis_symbol:
            candidates.extend([constituent.symbol, constituent.symbol.replace(".", "-")])
        last_error: Exception | None = None
        for symbol in dict.fromkeys(candidates):
            try:
                rows = await self.client.overseas_daily_chart(symbol, constituent.exchange)
                regular = await self.client.overseas_regular_close(symbol, constituent.exchange, target_date)
                if rows:
                    return rows, regular
            except Exception as exc:
                last_error = exc
        raise last_error or RuntimeError("KIS returned no daily bars")
