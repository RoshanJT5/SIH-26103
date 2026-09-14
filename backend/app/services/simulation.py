from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ProjectSnapshot, RiskPrediction, Dataset
from ..services.risk import implementation_risk, calculate_risk_score, risk_band


def _latest(session, sid):
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == sid)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


def simulate(
    session,
    project_id,
    revised_cost_cr=None,
    expenditure_cr=None,
    physical_progress_pct=None,
    schedule_revision_days=None,
):
    snap = session.scalar(
        select(ProjectSnapshot)
        .join(Dataset)
        .where(ProjectSnapshot.project_id == project_id, Dataset.status == "completed")
        .order_by(ProjectSnapshot.id.desc())
    )
    if not snap:
        return None
    pred = _latest(session, snap.id)

    # build mutated snapshot shallow copy for implementation risk
    class Temp:
        pass

    tmp = Temp()
    for field in [
        "physical_progress_pct",
        "original_cost_cr",
        "revised_cost_cr",
        "expenditure_cr",
        "original_commissioning_date",
        "revised_commissioning_date",
        "sanction_date",
        "sector",
        "ministry",
        "implementing_agency",
    ]:
        setattr(tmp, field, getattr(snap, field))
    if physical_progress_pct is not None:
        tmp.physical_progress_pct = Decimal(str(physical_progress_pct))
    if revised_cost_cr is not None:
        tmp.revised_cost_cr = Decimal(str(revised_cost_cr))
    if expenditure_cr is not None:
        tmp.expenditure_cr = Decimal(str(expenditure_cr))
    # schedule revision override: adjust revised date
    if schedule_revision_days is not None:
        from datetime import timedelta

        tmp.revised_commissioning_date = snap.original_commissioning_date + timedelta(
            days=int(schedule_revision_days)
        )
    # implementation risk
    impl = implementation_risk(tmp, source_as_of_date=snap.dataset.source_as_of_date)
    # cost/time probabilities: keep original if not changed, else simple heuristic: if revised cost increased, increase cost prob proportionally; progress low increases both
    cost_prob = (
        pred.cost_risk_probability
        if pred and pred.cost_risk_probability is not None
        else Decimal("0.5")
    )
    time_prob = (
        pred.time_risk_probability
        if pred and pred.time_risk_probability is not None
        else Decimal("0.5")
    )
    # heuristic adjustments
    if revised_cost_cr is not None:
        delta = (
            (Decimal(str(revised_cost_cr)) - snap.original_cost_cr)
            / snap.original_cost_cr
            if snap.original_cost_cr
            else Decimal("0")
        )
        cost_prob = max(
            Decimal("0"), min(Decimal("1"), cost_prob + delta * Decimal("0.5"))
        )
    if physical_progress_pct is not None:
        # lower progress raises time risk
        prog = Decimal(str(physical_progress_pct))
        time_prob = max(
            Decimal("0"),
            min(Decimal("1"), time_prob + (Decimal("50") - prog) / Decimal("200")),
        )
    impl_score = (
        impl.score
        if impl.score is not None
        else pred.implementation_score
        if pred
        else None
    )
    rs = calculate_risk_score(cost_prob, time_prob, impl_score)
    orig_score = pred.overall_score if pred else None
    orig_band = pred.risk_band if pred else None
    assumptions = [
        "Cost/time probabilities adjusted heuristically for simulation; illustrative only.",
        "Implementation score recomputed from progress/expenditure/schedule.",
        "No persistence; snapshot history unchanged.",
    ]
    delta_score = (
        (rs.overall_score - orig_score)
        if rs.overall_score is not None and orig_score is not None
        else None
    )
    return {
        "project_id": project_id,
        "project_code": snap.project.project_code,
        "original_overall_score": orig_score,
        "original_band": orig_band,
        "simulated_overall_score": rs.overall_score,
        "simulated_band": rs.band,
        "delta": delta_score,
        "assumptions": assumptions,
    }
