from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ProjectSnapshot, RiskPrediction, Dataset


def _latest(session, sid):
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == sid)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


def build_forecast(session, project_id, horizon=3):
    snaps = session.scalars(
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project_id)
        .join(Dataset)
        .where(Dataset.status == "completed")
        .order_by(ProjectSnapshot.dataset_id.asc())
    ).all()
    if not snaps:
        return None
    hist = []
    for snap in snaps:
        pred = _latest(session, snap.id)
        hist.append(
            (
                snap,
                pred.overall_score if pred and pred.overall_score is not None else None,
            )
        )
    # deterministic linear trend if >=2 points
    scores = [v for _, v in hist if v is not None]
    points = []
    for snap, score in hist:
        points.append(
            {
                "dataset_id": snap.dataset_id,
                "source_as_of_date": snap.dataset.source_as_of_date,
                "overall_score": score,
                "is_forecast": False,
                "method": "observed",
            }
        )
    if len(scores) >= 2:
        slope = (scores[-1] - scores[0]) / Decimal(len(scores) - 1)
        last = scores[-1]
        for i in range(1, horizon + 1):
            f = last + slope * Decimal(i)
            f = max(Decimal("0"), min(Decimal("100"), f))
            f = f.quantize(Decimal("0.01"))
            points.append(
                {
                    "dataset_id": None,
                    "source_as_of_date": None,
                    "overall_score": f,
                    "is_forecast": True,
                    "method": "linear-trend",
                }
            )
    limitations = [
        "Deterministic linear trend on snapshot scores; illustrative only.",
        "Sparse history limits reliability.",
        "Not a validated future forecast without monthly history.",
    ]
    methodology = "observed history plus dashed linear-trend forecast (slope from first to last observed score)."
    return points, methodology, limitations
