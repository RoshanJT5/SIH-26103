from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ProjectSnapshot, Dataset
from ..services.features import derive_analytical_features


def build_trajectory(session, project_id):
    snaps = session.scalars(
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project_id)
        .join(Dataset)
        .where(Dataset.status == "completed")
        .order_by(ProjectSnapshot.dataset_id.asc())
    ).all()
    if not snaps:
        return None
    points = []
    for snap in snaps:
        features = derive_analytical_features(
            snap, source_as_of_date=snap.dataset.source_as_of_date
        )
        # expected progress = (project_age / planned_duration)*100 capped 0-100 if both available
        expected = None
        if (
            features.project_age_days is not None
            and features.planned_duration_days
            and features.planned_duration_days > 0
        ):
            exp = (
                Decimal(features.project_age_days)
                / Decimal(features.planned_duration_days)
                * Decimal("100")
            )
            exp = max(Decimal("0"), min(Decimal("100"), exp))
            expected = exp.quantize(Decimal("0.01"))
        actual = snap.physical_progress_pct
        dev = None
        if expected is not None:
            dev = (actual - expected).quantize(Decimal("0.01"))
        points.append(
            {
                "dataset_id": snap.dataset_id,
                "source_as_of_date": snap.dataset.source_as_of_date,
                "expected_progress": expected,
                "actual_progress": actual,
                "deviation": dev,
                "snapshot_id": snap.id,
            }
        )
    return points
