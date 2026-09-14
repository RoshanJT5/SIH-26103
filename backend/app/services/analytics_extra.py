from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict, Counter
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..models import (
    ProjectSnapshot,
    RiskPrediction,
    RiskExplanation,
    ModelVersion,
    Dataset,
)


def _latest(session, sid):
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == sid)
        .order_by(RiskPrediction.predicted_at.desc())
        .limit(1)
    )


def cost_drivers(session, limit=20):
    exps = session.scalars(select(RiskExplanation).limit(5000)).all()
    if not exps:
        return []
    by_feature = defaultdict(list)
    for e in exps:
        by_feature[e.feature_name].append(float(e.shap_contribution))
    out = []
    for feat, vals in by_feature.items():
        avg = sum(vals) / len(vals)
        out.append(
            {
                "feature": feat,
                "average_shap": Decimal(str(avg)).quantize(Decimal("0.0001")),
                "coverage": len(vals),
                "interpretation": "Positive pushes risk up; negative pushes down.",
            }
        )
    out.sort(key=lambda x: -abs(float(x["average_shap"])))
    return out[:limit]


def ministry_health(session, ministry):
    snaps = session.scalars(
        select(ProjectSnapshot)
        .join(Dataset)
        .where(Dataset.status == "completed", ProjectSnapshot.ministry == ministry)
    ).all()
    if not snaps:
        return None
    scores = []
    dist = Counter()
    for snap in snaps:
        pred = _latest(session, snap.id)
        if pred and pred.overall_score is not None:
            scores.append(pred.overall_score)
        band = pred.risk_band if pred and pred.risk_band else "unavailable"
        dist[band] += 1
    avg = None if not scores else sum(scores) / len(scores)
    high = dist.get("high", 0)
    crit = dist.get("critical", 0)
    return {
        "ministry": ministry,
        "project_count": len(snaps),
        "average_overall_score": avg,
        "high_risk_projects": high,
        "critical_projects": crit,
        "band_distribution": dict(dist),
        "methodology": "Aggregates of latest stored predictions per snapshot; average over available scores.",
        "limitations": ["Snapshot caveat.", "Unavailable scores excluded."],
    }


def geography(session):
    # illustrative: group by ministry as region proxy plus sector
    snaps = session.scalars(
        select(ProjectSnapshot).join(Dataset).where(Dataset.status == "completed")
    ).all()
    by_ministry = defaultdict(list)
    for s in snaps:
        by_ministry[s.ministry].append(s)
    out = []
    for region, lst in sorted(by_ministry.items()):
        scores = []
        high = crit = 0
        for snap in lst:
            pred = _latest(session, snap.id)
            if pred and pred.overall_score is not None:
                scores.append(pred.overall_score)
            if pred and pred.risk_band == "high":
                high += 1
            if pred and pred.risk_band == "critical":
                crit += 1
        avg = None if not scores else sum(scores) / len(scores)
        out.append(
            {
                "region": region,
                "project_count": len(lst),
                "average_overall_score": avg,
                "high_risk_projects": high + crit,
            }
        )
    return out


def timeline(session, project_id):
    snaps = session.scalars(
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project_id)
        .join(Dataset)
        .where(Dataset.status == "completed")
        .order_by(ProjectSnapshot.dataset_id.asc())
    ).all()
    if not snaps:
        return None
    pts = []
    for snap in snaps:
        pred = _latest(session, snap.id)
        pts.append(
            {
                "dataset_id": snap.dataset_id,
                "source_as_of_date": snap.dataset.source_as_of_date,
                "snapshot_id": snap.id,
                "overall_score": pred.overall_score if pred else None,
                "risk_band": pred.risk_band if pred else None,
                "physical_progress_pct": snap.physical_progress_pct,
                "expenditure_cr": snap.expenditure_cr,
            }
        )
    return pts


def list_models(session):
    return session.scalars(
        select(ModelVersion).order_by(ModelVersion.created_at.desc())
    ).all()


def performance(session):
    models = session.scalars(
        select(ModelVersion).order_by(ModelVersion.created_at.desc())
    ).all()
    if not models:
        return {
            "target_type": "cost",
            "latest_metrics": {},
            "comparison": [],
            "note": "No models trained yet. Run python -m ml.training.train.",
        }
    latest = models[0]
    comps = [
        {"id": m.id, "name": m.name, "target_type": m.target_type, "metrics": m.metrics}
        for m in models[:6]
    ]
    return {
        "target_type": latest.target_type,
        "latest_metrics": latest.metrics,
        "comparison": comps,
        "note": "Metrics from held-out test; compare honestly.",
    }
