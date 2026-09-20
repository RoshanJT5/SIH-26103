"""Add platform_updates table.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("related_dataset_id", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_updates")),
    )
    op.create_index(
        op.f("ix_platform_updates_category"),
        "platform_updates",
        ["category"],
        unique=False,
    )
    seed = sa.table(
        "platform_updates",
        sa.column("category", sa.String),
        sa.column("title", sa.String),
        sa.column("summary", sa.Text),
        sa.column("content", sa.Text),
        sa.column("status", sa.String),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("meta", sa.JSON),
    )

    def dt(s: str) -> datetime:
        return datetime.fromisoformat(s)

    op.bulk_insert(
        seed,
        [
            {
                "category": "dataset",
                "title": "Monitoring snapshot updated",
                "summary": "Latest infrastructure project monitoring snapshot has been processed and is available for analysis.",
                "content": "The September 2026 monitoring snapshot completed validation, including cost and schedule field checks. Data-quality details are available under Documents. All scoped metrics and risk scoring now reflect this snapshot.",
                "status": "published",
                "published_at": dt("2026-09-14T09:00:00+00:00"),
                "updated_at": dt("2026-09-14T09:00:00+00:00"),
                "created_at": dt("2026-09-14T09:00:00+00:00"),
                "meta": {"tag": "featured"},
            },
            {
                "category": "model",
                "title": "Risk model evaluation updated",
                "summary": "Latest model performance results are now available in the analytics section.",
                "content": "Cost-risk and time-risk classifiers were evaluated on held-out data with calibration via sigmoid. Metrics including precision, recall, F1, ROC-AUC and calibration (Brier) are published under Analytics → Model Performance.",
                "status": "published",
                "published_at": dt("2026-09-14T08:00:00+00:00"),
                "updated_at": dt("2026-09-14T08:00:00+00:00"),
                "created_at": dt("2026-09-14T08:00:00+00:00"),
                "meta": None,
            },
            {
                "category": "methodology",
                "title": "Risk methodology documentation updated",
                "summary": "Updated explanation of project risk scoring and analytical methodology.",
                "content": "Documentation now clarifies the 0–100 overall score (0.4×cost + 0.4×time + 0.2×implementation), risk bands, and the snapshot-based limitation that missing revised figures remain unavailable rather than being imputed.",
                "status": "published",
                "published_at": dt("2026-09-12T10:00:00+00:00"),
                "updated_at": dt("2026-09-12T10:00:00+00:00"),
                "created_at": dt("2026-09-12T10:00:00+00:00"),
                "meta": None,
            },
            {
                "category": "platform",
                "title": "Project monitoring records added",
                "summary": "New project monitoring records added to the snapshot.",
                "content": "Additional project records were ingested after CSV validation. Rejected rows remain listed with reasons in the data-quality report.",
                "status": "published",
                "published_at": dt("2026-09-10T09:00:00+00:00"),
                "updated_at": dt("2026-09-10T09:00:00+00:00"),
                "created_at": dt("2026-09-10T09:00:00+00:00"),
                "meta": None,
            },
            {
                "category": "monitoring",
                "title": "Early-warning signals enabled",
                "summary": "Risk escalation and progress-deviation signals now surface in the Early Warnings view.",
                "content": "Early warnings are generated from stored snapshot comparison without modifying project records. Each warning includes evidence and a suggested monitoring review.",
                "status": "published",
                "published_at": dt("2026-09-13T09:00:00+00:00"),
                "updated_at": dt("2026-09-13T09:00:00+00:00"),
                "created_at": dt("2026-09-13T09:00:00+00:00"),
                "meta": None,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_platform_updates_category"), table_name="platform_updates")
    op.drop_table("platform_updates")
