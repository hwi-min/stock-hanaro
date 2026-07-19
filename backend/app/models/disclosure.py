from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Disclosure(Base):
    __tablename__ = "disclosures"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    receipt_no: Mapped[str] = mapped_column(String(30), nullable=False, unique=True, index=True)
    corp_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    corp_name: Mapped[str] = mapped_column(String(150), nullable=False)
    stock_code: Mapped[str | None] = mapped_column(String(6), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    report_type: Mapped[str | None] = mapped_column(String(10))
    submitter: Mapped[str | None] = mapped_column(String(150))
    remarks: Mapped[str | None] = mapped_column(String(20))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    corp_cls: Mapped[str] = mapped_column(String(1), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    importance: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    is_correction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
