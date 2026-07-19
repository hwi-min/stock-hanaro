from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.kis import kis_client
from app.core.database import get_db
from app.market_catalog import stock_catalog
from app.models.market_quote import MarketQuote
from app.realtime import market_stream
from app.repositories.dashboard import DashboardRepository
from app.repositories.stock_master import StockMasterRepository

router = APIRouter(tags=["stocks"])


def number(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


@router.get("/search")
def search(q: str = Query(min_length=1, max_length=50), db: Session = Depends(get_db)):
    term = q.strip().lower()
    master_rows = StockMasterRepository(db).search(term, 8)
    stocks = [{"type": "stock", "id": row.symbol, "symbol": row.symbol, "name": row.name,
               "market": "kr", "label": f"{row.name} · {row.symbol}"} for row in master_rows]
    known_symbols = {item["id"] for item in stocks}
    stocks.extend({"type": "stock", "id": symbol, "symbol": symbol, "name": item["name"],
                   "market": item["market"], "label": f"{item['name']} · {symbol}"}
                  for symbol, item in stock_catalog().items()
                  if symbol not in known_symbols and (term in symbol.lower() or term in item["name"].lower()))
    issues = [{"type": "issue", "id": item["id"], "name": item["title"], "market": None,
               "label": item["title"]}
              for item in DashboardRepository(db).issues()
              if term in item["title"].lower() or term in item["summary"].lower()]
    return {"items": (stocks + issues)[:10]}


@router.get("/stocks/{symbol}")
async def stock_detail(symbol: str, interval: str = Query(default="daily", pattern="^(daily|weekly|monthly|minute)$"),
                       db: Session = Depends(get_db)):
    symbol = symbol.upper()
    metadata = stock_catalog().get(symbol)
    if metadata is None:
        master = StockMasterRepository(db).find(symbol)
        if master:
            metadata = {"name": master.name, "market": "kr", "exchange": "KRX",
                        "sector": master.market, "industry": "국내 상장주식"}
    if metadata is None:
        raise HTTPException(status_code=404, detail="stock is not in the supported catalog")

    if metadata["market"] == "kr":
        quote = await kis_client.domestic_price(symbol)
        live = market_stream.latest.get(symbol)
        if live:
            quote.update({"price": Decimal(str(live["price"])), "change": Decimal(str(live["change"])),
                          "change_pct": Decimal(str(live["change_pct"])),
                          "as_of": datetime.fromisoformat(live["as_of"]), "basis": "realtime"})
        else:
            quote["basis"] = "snapshot"
        period = {"daily": "D", "weekly": "W", "monthly": "M"}.get(interval)
        chart = await (kis_client.domestic_minute_chart(symbol) if interval == "minute"
                       else kis_client.domestic_chart(symbol, period or "D"))
        currency = "KRW"
    else:
        row = db.scalar(select(MarketQuote).where(
            MarketQuote.market == "us", MarketQuote.symbol == symbol).order_by(MarketQuote.collected_at.desc()))
        if row:
            quote = {"price": row.price, "change": row.change, "change_pct": row.change_pct,
                     "volume": row.volume, "as_of": row.as_of, "basis": "close"}
        else:
            fetched = await kis_client.overseas_price_detail(symbol, metadata["exchange"], metadata)
            quote = {"price": fetched.price, "change": fetched.change, "change_pct": fetched.change_pct,
                     "volume": fetched.volume, "as_of": fetched.as_of, "basis": "close"}
        chart = await kis_client.overseas_daily_chart(symbol, metadata["exchange"])
        if chart:
            latest = chart[-1]
            previous = chart[-2] if len(chart) > 1 else None
            quote["price"] = latest["close"]
            quote["volume"] = latest["volume"]
            if previous and previous["close"]:
                quote["change"] = latest["close"] - previous["close"]
                quote["change_pct"] = quote["change"] / previous["close"] * 100
        interval, currency = "daily", "USD"

    return {
        "symbol": symbol, "name": metadata["name"], "market": metadata["market"],
        "exchange": metadata["exchange"], "sector": metadata["sector"], "industry": metadata["industry"],
        "currency": currency, "price": number(quote["price"]), "change": number(quote.get("change")),
        "change_pct": number(quote.get("change_pct")), "volume": number(quote.get("volume")),
        "market_cap": number(quote.get("market_cap")), "per": number(quote.get("per")),
        "pbr": number(quote.get("pbr")), "foreign_ownership_pct": number(quote.get("foreign_ownership_pct")),
        "high_52w": number(quote.get("high_52w")), "low_52w": number(quote.get("low_52w")),
        "as_of": quote["as_of"].isoformat(), "basis": quote["basis"], "interval": interval,
        "session_date": chart[-1]["time"] if metadata["market"] == "us" and chart else None,
        "chart": [{key: number(value) if isinstance(value, Decimal) else value for key, value in point.items()}
                  for point in chart],
    }
