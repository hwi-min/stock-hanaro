from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Sp500Constituent(Base):
    __tablename__ = "sp500_constituents"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    kis_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    sector: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    industry: Mapped[str] = mapped_column(String(120), nullable=False)
    index_weight: Mapped[Decimal] = mapped_column(Numeric(14, 8), nullable=False)
    source_date: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Sp500DailySnapshot(Base):
    __tablename__ = "sp500_daily_snapshots"
    __table_args__ = (UniqueConstraint("trading_date", "symbol", name="uq_sp500_snapshot_date_symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trading_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(ForeignKey("sp500_constituents.symbol"), nullable=False, index=True)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    previous_close: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    change_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(28, 2))
    average_volume_20d: Mapped[Decimal | None] = mapped_column(Numeric(28, 2))
    dollar_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 2))
    relative_volume: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    index_weight: Mapped[Decimal] = mapped_column(Numeric(14, 8), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
