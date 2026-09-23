from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..models import (
    EarlyWarning,
    Dataset,
    ProjectSnapshot,
    RiskPrediction,
    IngestionIssue,
)
from ..services.features import derive_analytical_features

VERSION = "early-warning-v1"
BAND_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _latest(session, sid):
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == sid)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


def _key(project_id, dataset_id, typ):
    return f"{project_id}:{dataset_id}:{typ}"


def generate_for_snapshot(session, snapshot, prediction=None):
    if prediction is None:
        prediction = _latest(session, snapshot.id)
    dataset = snapshot.dataset
    project_id = snapshot.project_id
    dataset_id = snapshot.dataset_id
    warnings = []
    # risk escalation
    snaps = session.scalars(
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_id == project_id)
        .join(Dataset)
        .where(Dataset.status == "completed")
        .order_by(ProjectSnapshot.dataset_id.asc())
    ).all()
    if len(snaps) >= 2:
        prev = snaps[-2] if snaps[-1].id == snapshot.id else None
        # find previous
        idx = next((i for i, s in enumerate(snaps) if s.id == snapshot.id), None)
        if idx is not None and idx > 0:
            prev = snaps[idx - 1]
            prev_pred = _latest(session, prev.id)
            cur_band = prediction.risk_band if prediction else None
            prev_band = prev_pred.risk_band if prev_pred else None
            if cur_band in BAND_ORDER and prev_band in BAND_ORDER:
                if BAND_ORDER[cur_band] > BAND_ORDER[prev_band]:
                    warnings.append(
                        (
                            "risk_escalation",
                            "high" if cur_band == "high" else "critical",
                            f"Risk escalated {prev_band} → {cur_band}",
                            {
                                "previous_band": prev_band,
                                "current_band": cur_band,
                                "previous_score": str(prev_pred.overall_score)
                                if prev_pred and prev_pred.overall_score
                                else None,
                                "current_score": str(prediction.overall_score)
                                if prediction and prediction.overall_score
                                else None,
                            },
                            "Review risk drivers and peer comparison.",
                        )
                    )
                if BAND_ORDER[cur_band] - BAND_ORDER[prev_band] >= 2:
                    warnings.append(
                        (
                            "rapid_deterioration",
                            "critical",
                            "Rapid deterioration (band jump)",
                            {"previous_band": prev_band, "current_band": cur_band},
                            "Immediate implementation review required.",
                        )
                    )
            if (
                prediction
                and prev_pred
                and prediction.overall_score is not None
                and prev_pred.overall_score is not None
            ):
                ch = prediction.overall_score - prev_pred.overall_score
                if ch >= Decimal("20"):
                    warnings.append(
                        (
                            "rapid_deterioration",
                            "critical",
                            f"Score jumped +{ch:.1f}",
                            {"score_change": str(ch)},
                            "Escalate monitoring.",
                        )
                    )
    # progress deviation
    features = derive_analytical_features(
        snapshot, source_as_of_date=dataset.source_as_of_date
    )
    if (
        features.expenditure_to_original_cost_ratio is not None
        and snapshot.physical_progress_pct is not None
    ):
        dev = features.expenditure_to_original_cost_ratio - (
            snapshot.physical_progress_pct / Decimal("100")
        )
        if dev >= Decimal("0.25"):
            warnings.append(
                (
                    "expenditure_deviation",
                    "high",
                    "Expenditure materially ahead of progress",
                    {"deviation": str(dev)},
                    "Reconcile expenditure vs physical progress.",
                )
            )
        elif dev >= Decimal("0.10"):
            warnings.append(
                (
                    "progress_deviation",
                    "watch",
                    "Expenditure ahead of progress",
                    {"deviation": str(dev)},
                    "Check progress reporting lag.",
                )
            )
    if (
        features.cost_escalation_pct is not None
        and features.cost_escalation_pct > Decimal("20")
    ):
        warnings.append(
            (
                "cost_escalation",
                "high",
                f"Cost escalation {features.cost_escalation_pct:.1f}%",
                {"cost_escalation_pct": str(features.cost_escalation_pct)},
                "Review budget and funding.",
            )
        )
    if (
        features.schedule_revision_days is not None
        and features.schedule_revision_days >= 365
    ):
        warnings.append(
            (
                "schedule_slippage",
                "high",
                f"Schedule slippage {features.schedule_revision_days} days",
                {"schedule_revision_days": features.schedule_revision_days},
                "Review timeline and dependencies.",
            )
        )
    elif (
        features.schedule_revision_days is not None
        and features.schedule_revision_days >= 180
    ):
        warnings.append(
            (
                "schedule_slippage",
                "watch",
                f"Schedule slippage {features.schedule_revision_days} days",
                {"schedule_revision_days": features.schedule_revision_days},
                "Monitor schedule buffer.",
            )
        )
    return warnings


def ensure_warnings(session, limit=1000):
    existing_count = session.scalar(select(func.count()).select_from(EarlyWarning))
    if existing_count and existing_count > 0:
        return
    snaps = session.scalars(
        select(ProjectSnapshot)
        .join(Dataset)
        .where(Dataset.status == "completed")
        .order_by(ProjectSnapshot.id.desc())
        .limit(limit)
    ).all()
    for snap in snaps:
        pred = _latest(session, snap.id)
        for typ, sev, title, evidence, review in generate_for_snapshot(
            session, snap, pred
        ):
            dk = _key(snap.project_id, snap.dataset_id, typ)
            exists = session.scalar(
                select(EarlyWarning).where(EarlyWarning.deduplication_key == dk)
            )
            if exists:
                continue
            ew = EarlyWarning(
                project_id=snap.project_id,
                dataset_id=snap.dataset_id,
                snapshot_id=snap.id,
                prediction_id=pred.id if pred else None,
                type=typ,
                severity=sev,
                title=title,
                description=title,
                evidence=evidence,
                recommended_review=review,
                status="open",
                deduplication_key=dk,
            )
            session.add(ew)
    try:
        session.commit()
    except Exception:
        session.rollback()



def enriched(session, ew):
    snap = session.get(ProjectSnapshot, ew.snapshot_id)
    proj = snap.project if snap else None
    return {
        "project_code": proj.project_code if proj else None,
        "project_name": snap.project_name if snap else None,
        "sector": snap.sector if snap else None,
        "ministry": snap.ministry if snap else None,
    }
