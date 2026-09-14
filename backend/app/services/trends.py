from decimal import Decimal
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Dataset, ProjectSnapshot, RiskPrediction

VERSION = "risk-trends-v1"


def classify_trend(change):
    if change is None:
        return "stable"
    v = float(change)
    if v <= -5:
        return "improving"
    if v <= 5:
        return "stable"
    if v <= 10:
        return "watch"
    if v <= 20:
        return "deteriorating"
    return "rapid_deterioration"


def _latest(session, sid):
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == sid)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


def get_trends(
    session,
    dataset_id=None,
    project_id=None,
    sector=None,
    ministry=None,
    min_change=None,
    limit=100,
    offset=0,
):
    completed = session.scalars(
        select(Dataset).where(Dataset.status == "completed").order_by(Dataset.id.asc())
    ).all()
    if not completed:
        return [], 0
    snaps = session.scalars(
        select(ProjectSnapshot).join(Dataset).where(Dataset.status == "completed")
    ).all()
    by_project = defaultdict(list)
    for s in snaps:
        by_project[s.project_id].append(s)
    items = []
    for pid, slist in by_project.items():
        if project_id is not None and pid != project_id:
            continue
        latest = max(slist, key=lambda x: x.id)
        if sector and latest.sector != sector:
            continue
        if ministry and latest.ministry != ministry:
            continue
        if dataset_id is not None and not any(
            x.dataset_id == dataset_id for x in slist
        ):
            continue
        snaps_sorted = sorted(slist, key=lambda x: x.dataset_id)
        history = []
        for snap in snaps_sorted:
            pred = _latest(session, snap.id)
            ds = snap.dataset
            history.append(
                {
                    "dataset_id": ds.id,
                    "source_name": ds.source_name,
                    "source_as_of_date": ds.source_as_of_date,
                    "imported_at": ds.imported_at,
                    "snapshot_id": snap.id,
                    "overall_score": pred.overall_score if pred else None,
                    "risk_band": pred.risk_band if pred else None,
                    "cost_risk_probability": pred.cost_risk_probability
                    if pred
                    else None,
                    "time_risk_probability": pred.time_risk_probability
                    if pred
                    else None,
                }
            )
        scores = [h["overall_score"] for h in history if h["overall_score"] is not None]
        first = scores[0] if scores else None
        last = scores[-1] if scores else None
        change = (last - first) if first is not None and last is not None else None
        trend = classify_trend(change)
        if min_change is not None and (
            change is None or float(change) < float(min_change)
        ):
            continue
        items.append(
            {
                "project_id": pid,
                "project_code": latest.project.project_code,
                "project_name": latest.project_name,
                "sector": latest.sector,
                "ministry": latest.ministry,
                "implementing_agency": latest.implementing_agency,
                "history": history,
                "first_score": first,
                "last_score": last,
                "score_change": change,
                "trend": trend,
                "trend_label": trend,
            }
        )
    items.sort(
        key=lambda x: (
            x["score_change"] is None,
            -(float(x["score_change"]) if x["score_change"] is not None else 0),
            x["project_id"],
        )
    )
    total = len(items)
    paged = items[offset : offset + limit]
    return paged, total
