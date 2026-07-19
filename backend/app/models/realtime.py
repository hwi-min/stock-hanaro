from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RealtimeSubscription(Base):
    __tablename__ = "realtime_subscriptions"

    symbol: Mapped[str] = mapped_column(String(12), primary_key=True)
    viewer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RealtimeWorkerState(Base):
    __tablename__ = "realtime_worker_states"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    configured_stock_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_subscription_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_tick_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
