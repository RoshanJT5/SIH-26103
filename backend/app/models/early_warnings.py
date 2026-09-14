"""Early warnings — computed early-warning signals with acknowledge/close workflow."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base, utc_now


class EarlyWarning(Base):
    __tablename__ = "early_warnings"
    __table_args__ = (
        CheckConstraint("severity IN ('watch','high','critical')", name="severity"),
        CheckConstraint("status IN ('open','acknowledged','closed')", name="status"),
        CheckConstraint(
            "type IN ('risk_escalation','progress_deviation','cost_escalation','schedule_slippage','stale_data','rapid_deterioration','expenditure_deviation')",
            name="type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("project_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prediction_id: Mapped[int | None] = mapped_column(
        ForeignKey("risk_predictions.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    recommended_review: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="open", nullable=False, index=True
    )
    deduplication_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    detected_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    data_date: Mapped[datetime | None] = mapped_column(default=None)
