from datetime import datetime

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, utc_now


class PlatformUpdate(Base):
    __tablename__ = "platform_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="published")
    related_dataset_id: Mapped[int | None] = mapped_column(nullable=True)
    published_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=utc_now, onupdate=utc_now
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
