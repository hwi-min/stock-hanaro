from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_report_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    broker: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    analyst: Mapped[str | None] = mapped_column(String(200), index=True)
    published_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    stock_code: Mapped[str | None] = mapped_column(String(12), index=True)
    stock_name: Mapped[str | None] = mapped_column(String(100), index=True)
    opinion: Mapped[str | None] = mapped_column(String(40))
    target_price: Mapped[int | None] = mapped_column(Integer)
    previous_target_price: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

