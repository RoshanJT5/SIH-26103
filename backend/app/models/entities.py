from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, utc_now


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed', 'failed')", name="status"),
        CheckConstraint("accepted_count >= 0", name="accepted_count_nonnegative"),
        CheckConstraint("rejected_count >= 0", name="rejected_count_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    source_as_of_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    snapshots: Mapped[list["ProjectSnapshot"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    snapshots: Mapped[list["ProjectSnapshot"]] = relationship(back_populates="project")


class ProjectSnapshot(Base):
    __tablename__ = "project_snapshots"
    __table_args__ = (
        UniqueConstraint("project_id", "dataset_id", name="uq_snapshot_project_dataset"),
        CheckConstraint("original_cost_cr > 0", name="original_cost_positive"),
        CheckConstraint("revised_cost_cr IS NULL OR revised_cost_cr >= 0", name="revised_cost_nonnegative"),
        CheckConstraint("expenditure_cr >= 0", name="expenditure_nonnegative"),
        CheckConstraint("physical_progress_pct >= 0 AND physical_progress_pct <= 100", name="progress_range"),
        Index("ix_snapshots_dataset_sector", "dataset_id", "sector"),
        Index("ix_snapshots_dataset_ministry", "dataset_id", "ministry"),
        Index("ix_snapshots_dataset_agency", "dataset_id", "implementing_agency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    project_name: Mapped[str] = mapped_column(String(500), nullable=False)
    sector: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ministry: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    implementing_agency: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    original_cost_cr: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    revised_cost_cr: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    expenditure_cr: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    physical_progress_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    original_commissioning_date: Mapped[date] = mapped_column(Date, nullable=False)
    revised_commissioning_date: Mapped[date | None] = mapped_column(Date)
    sanction_date: Mapped[date | None] = mapped_column(Date)
    raw_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    quality_flags: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    project: Mapped[Project] = relationship(back_populates="snapshots")
    dataset: Mapped[Dataset] = relationship(back_populates="snapshots")


class IngestionIssue(Base):
    __tablename__ = "ingestion_issues"
    __table_args__ = (CheckConstraint("severity IN ('info', 'warning', 'error')", name="severity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    field: Mapped[str | None] = mapped_column(String(128))
    raw_value: Mapped[str | None] = mapped_column(Text)
    issue_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (CheckConstraint("target_type IN ('cost', 'time')", name="target_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    target_definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    feature_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    artifact_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    training_dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False)
    split_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    calibration_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RiskPrediction(Base):
    __tablename__ = "risk_predictions"
    __table_args__ = (
        CheckConstraint("availability_status IN ('available', 'partial', 'unavailable')", name="availability_status"),
        CheckConstraint("cost_risk_probability IS NULL OR (cost_risk_probability >= 0 AND cost_risk_probability <= 1)", name="cost_probability_range"),
        CheckConstraint("time_risk_probability IS NULL OR (time_risk_probability >= 0 AND time_risk_probability <= 1)", name="time_probability_range"),
        CheckConstraint("implementation_score IS NULL OR (implementation_score >= 0 AND implementation_score <= 100)", name="implementation_score_range"),
        CheckConstraint("overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 100)", name="overall_score_range"),
        CheckConstraint("risk_band IS NULL OR risk_band IN ('low', 'medium', 'high', 'critical')", name="risk_band"),
        UniqueConstraint("snapshot_id", "cost_model_version_id", "time_model_version_id", "rule_version", name="uq_prediction_version"),
        Index("ix_predictions_band_score", "risk_band", "overall_score"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("project_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    cost_model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id", ondelete="RESTRICT"))
    time_model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id", ondelete="RESTRICT"))
    cost_risk_probability: Mapped[Decimal | None] = mapped_column(Numeric(8, 7))
    time_risk_probability: Mapped[Decimal | None] = mapped_column(Numeric(8, 7))
    implementation_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_band: Mapped[str | None] = mapped_column(String(16), index=True)
    availability_status: Mapped[str] = mapped_column(String(16), nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RiskExplanation(Base):
    __tablename__ = "risk_explanations"
    __table_args__ = (CheckConstraint("output_scale IN ('raw', 'probability')", name="output_scale"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("risk_predictions.id", ondelete="CASCADE"), nullable=False, index=True)
    component_model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id", ondelete="RESTRICT"), nullable=False)
    feature_name: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_value: Mapped[Any | None] = mapped_column(JSON)
    shap_contribution: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    baseline_value: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    output_scale: Mapped[str] = mapped_column(String(32), nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('normal', 'watch', 'high', 'critical')", name="severity"),
        CheckConstraint("status IN ('open', 'acknowledged', 'closed')", name="status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("project_snapshots.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("risk_predictions.id", ondelete="CASCADE"), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    deduplication_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (CheckConstraint("outcome IN ('success', 'failure')", name="outcome"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    operation: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id", ondelete="SET NULL"), index=True)
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id", ondelete="SET NULL"), index=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)

