"""Add early_warnings table for the early-warning center.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "early_warnings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("recommended_review", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_date", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "severity IN ('watch','high','critical')",
            name=op.f("ck_early_warnings_severity"),
        ),
        sa.CheckConstraint(
            "status IN ('open','acknowledged','closed')",
            name=op.f("ck_early_warnings_status"),
        ),
        sa.CheckConstraint(
            "type IN ('risk_escalation','progress_deviation','cost_escalation','schedule_slippage','stale_data','rapid_deterioration','expenditure_deviation')",
            name=op.f("ck_early_warnings_type"),
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name=op.f("fk_early_warnings_dataset_id_datasets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["risk_predictions.id"],
            name=op.f("fk_early_warnings_prediction_id_risk_predictions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_early_warnings_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["project_snapshots.id"],
            name=op.f("fk_early_warnings_snapshot_id_project_snapshots"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_early_warnings")),
        sa.UniqueConstraint(
            "deduplication_key", name=op.f("uq_early_warnings_deduplication_key")
        ),
    )
    op.create_index(
        op.f("ix_early_warnings_dataset_id"),
        "early_warnings",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_early_warnings_project_id"),
        "early_warnings",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_early_warnings_severity"), "early_warnings", ["severity"], unique=False
    )
    op.create_index(
        op.f("ix_early_warnings_snapshot_id"),
        "early_warnings",
        ["snapshot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_early_warnings_status"), "early_warnings", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_early_warnings_type"), "early_warnings", ["type"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_early_warnings_type"), table_name="early_warnings")
    op.drop_index(op.f("ix_early_warnings_status"), table_name="early_warnings")
    op.drop_index(op.f("ix_early_warnings_snapshot_id"), table_name="early_warnings")
    op.drop_index(op.f("ix_early_warnings_severity"), table_name="early_warnings")
    op.drop_index(op.f("ix_early_warnings_project_id"), table_name="early_warnings")
    op.drop_index(op.f("ix_early_warnings_dataset_id"), table_name="early_warnings")
    op.drop_table("early_warnings")
