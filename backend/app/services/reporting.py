from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ProjectSnapshot, RiskPrediction, RiskExplanation, Dataset
from ..services.features import derive_analytical_features


def build_report(session, project_id):
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
    explanations = (
        session.scalars(
            select(RiskExplanation)
            .where(RiskExplanation.prediction_id == pred.id)
            .order_by(RiskExplanation.shap_contribution.desc())
            .limit(5)
        ).all()
        if pred
        else []
    )
    sections = []
    sections.append(
        {
            "title": "Executive Summary",
            "body": f"Project {snap.project.project_code} — {snap.project_name} in {snap.sector} ({snap.ministry}) has stored risk {pred.risk_band if pred else 'unavailable'} with score {pred.overall_score if pred and pred.overall_score else 'unavailable'}/100.",
        }
    )
    sections.append(
        {
            "title": "Project Facts",
            "body": f"Original cost {snap.original_cost_cr} cr, revised {snap.revised_cost_cr}, expenditure {snap.expenditure_cr} cr, progress {snap.physical_progress_pct}%.",
        }
    )
    sections.append(
        {
            "title": "Cost & Schedule Deviations",
            "body": f"Cost escalation {features.cost_escalation_pct}, schedule revision {features.schedule_revision_days} days, expenditure/original {features.expenditure_to_original_cost_ratio}.",
        }
    )
    drivers = (
        ", ".join(
            f"{e.feature_name} ({e.shap_contribution:+.3f})" for e in explanations
        )
        or "No stored SHAP drivers"
    )
    sections.append({"title": "Risk Drivers", "body": drivers})
    sections.append(
        {
            "title": "Peer Benchmark",
            "body": "See GET /analytics/benchmarks for cohort comparison; sparse cohorts noted as unavailable.",
        }
    )
    sections.append(
        {
            "title": "Recommended Review",
            "body": "See GET /projects/{id}/recommendations for 1-5 rule-based actions.",
        }
    )
    sections.append(
        {
            "title": "Data Quality & Limitations",
            "body": "Missing fields shown as unavailable; snapshot prototype caveat applies.",
        }
    )
    return {
        "project_id": project_id,
        "project_code": snap.project.project_code,
        "project_name": snap.project_name,
        "generated_at": datetime.now(timezone.utc),
        "dataset": {
            "dataset_id": snap.dataset_id,
            "source_name": snap.dataset.source_name,
            "source_as_of_date": str(snap.dataset.source_as_of_date)
            if snap.dataset.source_as_of_date
            else None,
        },
        "overall_score": pred.overall_score if pred else None,
        "risk_band": pred.risk_band if pred else None,
        "sections": sections,
        "limitations": [
            "Snapshot classification; not a validated forecast.",
            "Unavailable fields not imputed.",
            "Scores are model outputs, not facts.",
        ],
    }
