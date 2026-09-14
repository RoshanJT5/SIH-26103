from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ProjectSnapshot, RiskPrediction, Dataset
from ..services.features import derive_analytical_features


def build_recommendations(session, project_id):
    snap = session.scalar(
        select(ProjectSnapshot)
        .join(Dataset)
        .where(ProjectSnapshot.project_id == project_id, Dataset.status == "completed")
        .order_by(ProjectSnapshot.id.desc())
    )
    if not snap:
        return None
    pred = session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == snap.id)
        .order_by(RiskPrediction.predicted_at.desc())
        .limit(1)
    )
    features = derive_analytical_features(
        snap, source_as_of_date=snap.dataset.source_as_of_date
    )
    cands = []
    if (
        features.schedule_revision_days is not None
        and features.schedule_revision_days >= 180
    ):
        cands.append(
            (
                "Investigate schedule bottlenecks and contractor milestones",
                f"Schedule revision {features.schedule_revision_days} days",
                "Schedule slippage indicates execution delay.",
            )
        )
    if (
        features.cost_escalation_pct is not None
        and float(features.cost_escalation_pct) > 20
    ):
        cands.append(
            (
                "Review cost escalation and funding alignment",
                f"Cost escalation {features.cost_escalation_pct:.1f}%",
                "Revised cost materially above original.",
            )
        )
    if (
        features.expenditure_to_original_cost_ratio is not None
        and snap.physical_progress_pct is not None
    ):
        dev = (
            float(features.expenditure_to_original_cost_ratio)
            - float(snap.physical_progress_pct) / 100
        )
        if dev >= 0.25:
            cands.append(
                (
                    "Reconcile expenditure vs physical progress",
                    f"Deviation {dev:.2%}",
                    "High spend relative to reported progress.",
                )
            )
    if (
        snap.physical_progress_pct is not None
        and float(snap.physical_progress_pct) <= 25
    ):
        cands.append(
            (
                "Verify field progress and reporting completeness",
                f"Progress {snap.physical_progress_pct:.1f}%",
                "Very low physical progress.",
            )
        )
    if pred and pred.risk_band in ("high", "critical"):
        cands.append(
            (
                "Prioritize for detailed implementation review",
                f"Band {pred.risk_band} score {pred.overall_score}",
                "Stored risk in high band.",
            )
        )
    if not cands:
        cands.append(
            (
                "Continue routine monitoring",
                "No material deviations detected",
                "Project within expected ranges.",
            )
        )
    # take 1-5
    recs = []
    for i, (action, evidence, rationale) in enumerate(cands[:5], start=1):
        recs.append(
            {
                "priority": i,
                "action": action,
                "rationale": rationale,
                "evidence": evidence,
            }
        )
    methodology = "Rule-based 1-5 actions from schedule, cost, expenditure/progress, and risk band; never invents missing data."
    limitations = [
        "Recommendations are checks, not instructions.",
        "Missing fields stay unavailable.",
        "Snapshot classification caveat applies.",
    ]
    return {
        "project_code": snap.project.project_code,
        "items": recs,
        "methodology": methodology,
        "limitations": limitations,
    }
