from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from ..models import Dataset, ProjectSnapshot, RiskPrediction
from ..services.features import derive_analytical_features
from ..services.prediction_loader import (
    get_latest_predictions_map,
    get_cached,
    set_cached,
)

VERSION = "intervention-v1"
FORMULA = "priority = 0.35*overall_score + 0.15*max(0,score_change) + 0.15*cost_prob*100 + 0.15*time_prob*100 + 0.10*financial_exposure_norm + 0.10*progress_deviation*100"


def _latest(session, sid):
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == sid)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


def _trend_change(session, project_id):
    snaps = session.scalars(
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project_id)
        .join(Dataset)
        .where(Dataset.status == "completed")
        .order_by(ProjectSnapshot.dataset_id.asc())
    ).all()
    scores = []
    for s in snaps:
        p = _latest(session, s.id)
        if p and p.overall_score is not None:
            scores.append(p.overall_score)
    if len(scores) >= 2:
        return scores[-1] - scores[0]
    return Decimal("0")


def compute_priority(session, snapshot, pred=None, change=None):
    if pred is None:
        pred = _latest(session, snapshot.id)
    overall = (
        pred.overall_score if pred and pred.overall_score is not None else Decimal("0")
    )
    cost = (
        pred.cost_risk_probability * Decimal("100")
        if pred and pred.cost_risk_probability is not None
        else Decimal("0")
    )
    time = (
        pred.time_risk_probability * Decimal("100")
        if pred and pred.time_risk_probability is not None
        else Decimal("0")
    )
    features = derive_analytical_features(
        snapshot, source_as_of_date=snapshot.dataset.source_as_of_date
    )
    deviation = features.expenditure_to_original_cost_ratio
    prog = snapshot.physical_progress_pct
    if deviation is not None and prog is not None:
        prog_dev = max(Decimal("0"), deviation - (prog / Decimal("100")))
    else:
        prog_dev = Decimal("0")
    rev = snapshot.revised_cost_cr or snapshot.original_cost_cr
    fin_norm = (
        min(Decimal("100"), (rev / Decimal("5000") * Decimal("100")))
        if rev
        else Decimal("0")
    )
    if change is None:
        change = _trend_change(session, snapshot.project_id)
    det = max(Decimal("0"), change)
    priority = (
        Decimal("0.35") * overall
        + Decimal("0.15") * det
        + Decimal("0.15") * cost
        + Decimal("0.15") * time
        + Decimal("0.10") * fin_norm
        + Decimal("0.10") * prog_dev * Decimal("100")
    )
    priority = priority.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    drivers = []
    drivers.append(
        {
            "factor": "overall_score",
            "weight": Decimal("0.35"),
            "contribution": (Decimal("0.35") * overall).quantize(Decimal("0.01")),
            "detail": f"overall {overall}",
        }
    )
    drivers.append(
        {
            "factor": "deterioration",
            "weight": Decimal("0.15"),
            "contribution": (Decimal("0.15") * det).quantize(Decimal("0.01")),
            "detail": f"change {change:+.2f}",
        }
    )
    drivers.append(
        {
            "factor": "cost_prob",
            "weight": Decimal("0.15"),
            "contribution": (Decimal("0.15") * cost).quantize(Decimal("0.01")),
            "detail": f"{cost:.1f}%",
        }
    )
    drivers.append(
        {
            "factor": "time_prob",
            "weight": Decimal("0.15"),
            "contribution": (Decimal("0.15") * time).quantize(Decimal("0.01")),
            "detail": f"{time:.1f}%",
        }
    )
    drivers.append(
        {
            "factor": "financial_exposure",
            "weight": Decimal("0.10"),
            "contribution": (Decimal("0.10") * fin_norm).quantize(Decimal("0.01")),
            "detail": f"{rev} cr",
        }
    )
    drivers.append(
        {
            "factor": "progress_deviation",
            "weight": Decimal("0.10"),
            "contribution": (Decimal("0.10") * prog_dev * Decimal("100")).quantize(
                Decimal("0.01")
            ),
            "detail": f"dev {prog_dev:.3f}",
        }
    )
    return priority, drivers, pred


def list_priorities(session, limit=100, offset=0, sector=None, ministry=None):
    cache_key = f"priorities:{limit}:{offset}:{sector}:{ministry}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    snaps = session.scalars(
        select(ProjectSnapshot)
        .options(
            joinedload(ProjectSnapshot.project),
            joinedload(ProjectSnapshot.dataset),
        )
        .join(Dataset)
        .where(Dataset.status == "completed")
        .order_by(ProjectSnapshot.id.desc())
    ).all()
    seen = {}
    for s in snaps:
        if s.project_id not in seen:
            seen[s.project_id] = s
    latest = list(seen.values())
    if sector:
        latest = [s for s in latest if s.sector == sector]
    if ministry:
        latest = [s for s in latest if s.ministry == ministry]

    # Bulk load predictions for all snaps in one query
    all_sids = [s.id for s in snaps]
    preds_map = get_latest_predictions_map(session, all_sids)

    # Compute trend changes per project in memory
    snaps_by_project: dict[int, list[ProjectSnapshot]] = {}
    for s in snaps:
        snaps_by_project.setdefault(s.project_id, []).append(s)

    trend_changes: dict[int, Decimal] = {}
    for pid, psnaps in snaps_by_project.items():
        psnaps_sorted = sorted(psnaps, key=lambda x: x.dataset_id)
        scores = []
        for s in psnaps_sorted:
            p = preds_map.get(s.id)
            if p and p.overall_score is not None:
                scores.append(p.overall_score)
        if len(scores) >= 2:
            trend_changes[pid] = scores[-1] - scores[0]
        else:
            trend_changes[pid] = Decimal("0")

    scored = []
    for s in latest:
        priority, drivers, pred = compute_priority(
            session,
            s,
            pred=preds_map.get(s.id),
            change=trend_changes.get(s.project_id, Decimal("0")),
        )
        scored.append((priority, s, drivers, pred))
    scored.sort(key=lambda x: (-float(x[0]), x[1].project_id))
    total = len(scored)
    paged = scored[offset : offset + limit]
    items = []
    for idx, (priority, s, drivers, pred) in enumerate(paged, start=offset + 1):
        items.append(
            {
                "snapshot": s,
                "priority": priority,
                "drivers": drivers,
                "pred": pred,
                "rank": idx,
            }
        )
    res = (items, total)
    set_cached(cache_key, res)
    return res
