"""Create the initial project monitoring schema.

Revision ID: 0001
Revises: None
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_as_of_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("accepted_count >= 0", name=op.f("ck_datasets_accepted_count_nonnegative")),
        sa.CheckConstraint("rejected_count >= 0", name=op.f("ck_datasets_rejected_count_nonnegative")),
        sa.CheckConstraint("status IN ('pending', 'completed', 'failed')", name=op.f("ck_datasets_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_datasets")),
        sa.UniqueConstraint("checksum", name=op.f("uq_datasets_checksum")),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_code", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("project_code", name=op.f("uq_projects_project_code")),
    )
    op.create_table(
        "project_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("project_name", sa.String(length=500), nullable=False),
        sa.Column("sector", sa.String(length=255), nullable=False),
        sa.Column("ministry", sa.String(length=255), nullable=False),
        sa.Column("implementing_agency", sa.String(length=500), nullable=False),
        sa.Column("original_cost_cr", sa.Numeric(18, 2), nullable=False),
        sa.Column("revised_cost_cr", sa.Numeric(18, 2), nullable=True),
        sa.Column("expenditure_cr", sa.Numeric(18, 2), nullable=False),
        sa.Column("physical_progress_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("original_commissioning_date", sa.Date(), nullable=False),
        sa.Column("revised_commissioning_date", sa.Date(), nullable=True),
        sa.Column("sanction_date", sa.Date(), nullable=True),
        sa.Column("raw_values", sa.JSON(), nullable=False),
        sa.Column("quality_flags", sa.JSON(), nullable=False),
        sa.CheckConstraint("expenditure_cr >= 0", name=op.f("ck_project_snapshots_expenditure_nonnegative")),
        sa.CheckConstraint("original_cost_cr > 0", name=op.f("ck_project_snapshots_original_cost_positive")),
        sa.CheckConstraint("physical_progress_pct >= 0 AND physical_progress_pct <= 100", name=op.f("ck_project_snapshots_progress_range")),
        sa.CheckConstraint("revised_cost_cr IS NULL OR revised_cost_cr >= 0", name=op.f("ck_project_snapshots_revised_cost_nonnegative")),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], name=op.f("fk_project_snapshots_dataset_id_datasets"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_project_snapshots_project_id_projects"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_snapshots")),
        sa.UniqueConstraint("project_id", "dataset_id", name="uq_snapshot_project_dataset"),
    )
    op.create_index(op.f("ix_project_snapshots_dataset_id"), "project_snapshots", ["dataset_id"])
    op.create_index(op.f("ix_project_snapshots_project_id"), "project_snapshots", ["project_id"])
    op.create_index(op.f("ix_project_snapshots_sector"), "project_snapshots", ["sector"])
    op.create_index(op.f("ix_project_snapshots_ministry"), "project_snapshots", ["ministry"])
    op.create_index(op.f("ix_project_snapshots_implementing_agency"), "project_snapshots", ["implementing_agency"])
    op.create_index("ix_snapshots_dataset_sector", "project_snapshots", ["dataset_id", "sector"])
    op.create_index("ix_snapshots_dataset_ministry", "project_snapshots", ["dataset_id", "ministry"])
    op.create_index("ix_snapshots_dataset_agency", "project_snapshots", ["dataset_id", "implementing_agency"])
    op.create_table(
        "ingestion_issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=128), nullable=True),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("issue_code", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.CheckConstraint("severity IN ('info', 'warning', 'error')", name=op.f("ck_ingestion_issues_severity")),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], name=op.f("fk_ingestion_issues_dataset_id_datasets"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_issues")),
    )
    op.create_index(op.f("ix_ingestion_issues_dataset_id"), "ingestion_issues", ["dataset_id"])
    op.create_index(op.f("ix_ingestion_issues_issue_code"), "ingestion_issues", ["issue_code"])
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_definition", sa.JSON(), nullable=False),
        sa.Column("feature_schema", sa.JSON(), nullable=False),
        sa.Column("artifact_reference", sa.String(length=500), nullable=False),
        sa.Column("artifact_checksum", sa.String(length=64), nullable=False),
        sa.Column("training_dataset_id", sa.Integer(), nullable=False),
        sa.Column("split_seed", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("calibration_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("target_type IN ('cost', 'time')", name=op.f("ck_model_versions_target_type")),
        sa.ForeignKeyConstraint(["training_dataset_id"], ["datasets.id"], name=op.f("fk_model_versions_training_dataset_id_datasets"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_versions")),
    )
    op.create_index(op.f("ix_model_versions_target_type"), "model_versions", ["target_type"])
    op.create_table(
        "risk_predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("cost_model_version_id", sa.Integer(), nullable=True),
        sa.Column("time_model_version_id", sa.Integer(), nullable=True),
        sa.Column("cost_risk_probability", sa.Numeric(8, 7), nullable=True),
        sa.Column("time_risk_probability", sa.Numeric(8, 7), nullable=True),
        sa.Column("implementation_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("risk_band", sa.String(length=16), nullable=True),
        sa.Column("availability_status", sa.String(length=16), nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("availability_status IN ('available', 'partial', 'unavailable')", name=op.f("ck_risk_predictions_availability_status")),
        sa.CheckConstraint("cost_risk_probability IS NULL OR (cost_risk_probability >= 0 AND cost_risk_probability <= 1)", name=op.f("ck_risk_predictions_cost_probability_range")),
        sa.CheckConstraint("implementation_score IS NULL OR (implementation_score >= 0 AND implementation_score <= 100)", name=op.f("ck_risk_predictions_implementation_score_range")),
        sa.CheckConstraint("overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 100)", name=op.f("ck_risk_predictions_overall_score_range")),
        sa.CheckConstraint("risk_band IS NULL OR risk_band IN ('low', 'medium', 'high', 'critical')", name=op.f("ck_risk_predictions_risk_band")),
        sa.CheckConstraint("time_risk_probability IS NULL OR (time_risk_probability >= 0 AND time_risk_probability <= 1)", name=op.f("ck_risk_predictions_time_probability_range")),
        sa.ForeignKeyConstraint(["cost_model_version_id"], ["model_versions.id"], name=op.f("fk_risk_predictions_cost_model_version_id_model_versions"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["project_snapshots.id"], name=op.f("fk_risk_predictions_snapshot_id_project_snapshots"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["time_model_version_id"], ["model_versions.id"], name=op.f("fk_risk_predictions_time_model_version_id_model_versions"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_predictions")),
        sa.UniqueConstraint("snapshot_id", "cost_model_version_id", "time_model_version_id", "rule_version", name="uq_prediction_version"),
    )
    op.create_index(op.f("ix_risk_predictions_snapshot_id"), "risk_predictions", ["snapshot_id"])
    op.create_index(op.f("ix_risk_predictions_risk_band"), "risk_predictions", ["risk_band"])
    op.create_index("ix_predictions_band_score", "risk_predictions", ["risk_band", "overall_score"])
    op.create_table(
        "risk_explanations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("component_model_version_id", sa.Integer(), nullable=False),
        sa.Column("feature_name", sa.String(length=255), nullable=False),
        sa.Column("feature_value", sa.JSON(), nullable=True),
        sa.Column("shap_contribution", sa.Numeric(18, 8), nullable=False),
        sa.Column("baseline_value", sa.Numeric(18, 8), nullable=False),
        sa.Column("output_scale", sa.String(length=32), nullable=False),
        sa.CheckConstraint("output_scale IN ('raw', 'probability')", name=op.f("ck_risk_explanations_output_scale")),
        sa.ForeignKeyConstraint(["component_model_version_id"], ["model_versions.id"], name=op.f("fk_risk_explanations_component_model_version_id_model_versions"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prediction_id"], ["risk_predictions.id"], name=op.f("fk_risk_explanations_prediction_id_risk_predictions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_explanations")),
    )
    op.create_index(op.f("ix_risk_explanations_prediction_id"), "risk_explanations", ["prediction_id"])
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("deduplication_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("severity IN ('normal', 'watch', 'high', 'critical')", name=op.f("ck_alerts_severity")),
        sa.CheckConstraint("status IN ('open', 'acknowledged', 'closed')", name=op.f("ck_alerts_status")),
        sa.ForeignKeyConstraint(["prediction_id"], ["risk_predictions.id"], name=op.f("fk_alerts_prediction_id_risk_predictions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["project_snapshots.id"], name=op.f("fk_alerts_snapshot_id_project_snapshots"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
        sa.UniqueConstraint("deduplication_key", name=op.f("uq_alerts_deduplication_key")),
    )
    op.create_index(op.f("ix_alerts_snapshot_id"), "alerts", ["snapshot_id"])
    op.create_index(op.f("ix_alerts_severity"), "alerts", ["severity"])
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=True),
        sa.Column("model_version_id", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.CheckConstraint("outcome IN ('success', 'failure')", name=op.f("ck_audit_events_outcome")),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], name=op.f("fk_audit_events_dataset_id_datasets"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], name=op.f("fk_audit_events_model_version_id_model_versions"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(op.f("ix_audit_events_operation"), "audit_events", ["operation"])
    op.create_index(op.f("ix_audit_events_dataset_id"), "audit_events", ["dataset_id"])
    op.create_index(op.f("ix_audit_events_model_version_id"), "audit_events", ["model_version_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("alerts")
    op.drop_table("risk_explanations")
    op.drop_table("risk_predictions")
    op.drop_table("model_versions")
    op.drop_table("ingestion_issues")
    op.drop_table("project_snapshots")
    op.drop_table("projects")
    op.drop_table("datasets")

