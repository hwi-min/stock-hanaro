from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StockMaster(Base):
    __tablename__ = "stock_masters"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(12), nullable=False, unique=True, index=True)
    isin: Mapped[str | None] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    market: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(10), nullable=False, default="ST")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
