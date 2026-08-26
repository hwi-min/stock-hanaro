from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.collectors.kis import DOMESTIC_INDICES, QuotePayload, kis_client
from app.core.config import settings
from app.core.database import get_db
from app.repositories.market import MarketRepository
from app.schemas.dashboard import DashboardResponse
from app.services.api_cache import ApiCacheService
from app.services.dashboard import DashboardService
from app.services.market_freshness import domestic_quote_ttl

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _quote_payload(value: dict) -> QuotePayload:
    numeric_fields = ("price", "change", "change_pct", "volume", "market_cap")
    normalized = {**value}
    for field in numeric_fields:
        normalized[field] = Decimal(str(value[field])) if value.get(field) is not None else None
    if isinstance(normalized.get("as_of"), str):
        normalized["as_of"] = datetime.fromisoformat(normalized["as_of"])
    return QuotePayload(**normalized)


async def _refresh_domestic_indices(db: Session) -> None:
    if not settings.kis_on_demand_refresh_enabled or not settings.kis_app_key or not settings.kis_app_secret:
        return
    cache = ApiCacheService(db)
    quotes: list[QuotePayload] = []
    for symbol, code, name in DOMESTIC_INDICES:
        try:
            value, _, _ = await cache.get_or_fetch(
                f"kis:kr:index:{symbol}",
                domestic_quote_ttl(surface="home"),
                lambda symbol=symbol, code=code, name=name: kis_client.domestic_index(symbol, code, name),
            )
            quotes.append(_quote_payload(value))
        except Exception:
            # The dashboard remains available with the last successful Supabase snapshot.
            continue
    if quotes:
        MarketRepository(db).upsert_many(quotes)


@router.get("/home", response_model=DashboardResponse)
async def get_home_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    await _refresh_domestic_indices(db)
    return DashboardService(db).get_home()
