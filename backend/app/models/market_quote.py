from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketQuote(Base):
    __tablename__ = "market_quotes"
    __table_args__ = (UniqueConstraint("provider", "market", "symbol", name="uq_market_quote_identity"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False, default="equity", index=True)
    exchange: Mapped[str | None] = mapped_column(String(20))
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(150))
    sector: Mapped[str | None] = mapped_column(String(80), index=True)
    industry: Mapped[str | None] = mapped_column(String(120))
    currency: Mapped[str | None] = mapped_column(String(10))
    price: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    change: Mapped[Decimal | None] = mapped_column(Numeric(24, 6))
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(28, 2))
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(28, 2))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
