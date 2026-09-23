from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from ..models import Project, ProjectSnapshot, RiskPrediction, Dataset
from ..services.risk import implementation_risk, calculate_risk_score, risk_band
from ..services.features import derive_analytical_features


def _latest(session: Session, sid: int) -> RiskPrediction | None:
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == sid)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


def simulate(
    session: Session,
    project_id: int | str,
    revised_cost_cr: Decimal | float | None = None,
    expenditure_cr: Decimal | float | None = None,
    physical_progress_pct: Decimal | float | None = None,
    schedule_revision_days: int | None = None,
) -> dict | None:
    # 1. Resolve project by numeric ID or project_code
    project = None
    try:
        numeric_id = int(str(project_id).strip())
        project = session.scalar(select(Project).where(Project.id == numeric_id))
    except (ValueError, TypeError):
        pass

    if not project:
        project = session.scalar(
            select(Project).where(Project.project_code == str(project_id).strip())
        )

    if not project:
        return None

    # 2. Retrieve latest snapshot
    snap = session.scalar(
        select(ProjectSnapshot)
        .options(joinedload(ProjectSnapshot.project), joinedload(ProjectSnapshot.dataset))
        .join(Dataset)
        .where(ProjectSnapshot.project_id == project.id, Dataset.status == "completed")
        .order_by(ProjectSnapshot.id.desc())
    )
    if not snap:
        snap = session.scalar(
            select(ProjectSnapshot)
            .options(joinedload(ProjectSnapshot.project), joinedload(ProjectSnapshot.dataset))
            .where(ProjectSnapshot.project_id == project.id)
            .order_by(ProjectSnapshot.id.desc())
        )
    if not snap:
        return None

    pred = _latest(session, snap.id)
    as_of = snap.dataset.source_as_of_date if snap.dataset else None
    features = derive_analytical_features(snap, source_as_of_date=as_of)

    # 3. Baseline respective values from existing project snapshot
    baseline_progress = snap.physical_progress_pct
    baseline_orig_cost = snap.original_cost_cr
    baseline_rev_cost = snap.revised_cost_cr if snap.revised_cost_cr is not None else snap.original_cost_cr
    baseline_exp = snap.expenditure_cr
    baseline_sched_days = features.schedule_revision_days or 0

    base_cost_prob = (
        pred.cost_risk_probability
        if (pred and pred.cost_risk_probability is not None)
        else Decimal("0.50")
    )
    base_time_prob = (
        pred.time_risk_probability
        if (pred and pred.time_risk_probability is not None)
        else Decimal("0.50")
    )
    base_impl_score = (
        pred.implementation_score
        if (pred and pred.implementation_score is not None)
        else Decimal("50.0")
    )
    orig_score = pred.overall_score if pred else None
    orig_band = pred.risk_band if pred else None

    orig_cost_score = (base_cost_prob * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    orig_time_score = (base_time_prob * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    orig_impl_score = (
        base_impl_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if base_impl_score is not None
        else None
    )

    # 4. Build mutated snapshot shallow copy for analytical and implementation risk engine
    class TempSnapshot:
        pass

    tmp = TempSnapshot()
    for field in [
        "id",
        "project_id",
        "dataset_id",
        "source_row_number",
        "project_name",
        "sector",
        "ministry",
        "implementing_agency",
        "original_cost_cr",
        "revised_cost_cr",
        "expenditure_cr",
        "physical_progress_pct",
        "original_commissioning_date",
        "revised_commissioning_date",
        "sanction_date",
        "raw_values",
        "quality_flags",
    ]:
        setattr(tmp, field, getattr(snap, field, None))
    tmp.dataset = snap.dataset

    assumptions: list[str] = []
    sim_cost_prob = base_cost_prob
    sim_time_prob = base_time_prob

    # 5. Evaluate physical progress delta
    if physical_progress_pct is not None:
        prog_val = Decimal(str(physical_progress_pct))
        tmp.physical_progress_pct = prog_val
        if baseline_progress is not None:
            prog_diff = prog_val - baseline_progress
            if abs(prog_diff) > Decimal("0.001"):
                time_adj = -(prog_diff / Decimal("100")) * Decimal("0.40")
                sim_time_prob = max(Decimal("0.02"), min(Decimal("0.98"), base_time_prob + time_adj))
                direction = "advanced" if prog_diff > 0 else "reduced"
                assumptions.append(f"Physical progress {direction} from {baseline_progress}% to {prog_val}%.")
        else:
            sim_time_prob = max(Decimal("0.02"), min(Decimal("0.98"), Decimal("1.0") - (prog_val / Decimal("100"))))
            assumptions.append(f"Physical progress set to {prog_val}%.")

    # 6. Evaluate revised cost delta
    if revised_cost_cr is not None:
        cost_val = Decimal(str(revised_cost_cr))
        tmp.revised_cost_cr = cost_val
        ref_cost = baseline_rev_cost or baseline_orig_cost
        if ref_cost and baseline_orig_cost:
            cost_diff = cost_val - ref_cost
            if abs(cost_diff) > Decimal("0.01"):
                cost_ratio_diff = cost_diff / baseline_orig_cost
                cost_adj = cost_ratio_diff * Decimal("0.35")
                sim_cost_prob = max(Decimal("0.02"), min(Decimal("0.98"), base_cost_prob + cost_adj))
                direction = "escalated" if cost_diff > 0 else "reduced"
                assumptions.append(f"Revised cost {direction} from ₹{ref_cost:,.2f} Cr to ₹{cost_val:,.2f} Cr.")
        else:
            assumptions.append(f"Revised cost set to ₹{cost_val:,.2f} Cr.")

    # 7. Evaluate expenditure delta
    if expenditure_cr is not None:
        exp_val = Decimal(str(expenditure_cr))
        tmp.expenditure_cr = exp_val
        if baseline_exp is not None and abs(exp_val - baseline_exp) > Decimal("0.01"):
            exp_diff = exp_val - baseline_exp
            direction = "increased" if exp_diff > 0 else "decreased"
            assumptions.append(f"Expenditure {direction} from ₹{baseline_exp:,.2f} Cr to ₹{exp_val:,.2f} Cr.")

    # 8. Evaluate schedule revision days
    if schedule_revision_days is not None:
        days_val = int(schedule_revision_days)
        base_date = snap.original_commissioning_date or snap.sanction_date
        if base_date:
            tmp.revised_commissioning_date = base_date + timedelta(days=days_val)
        if abs(days_val - baseline_sched_days) > 0:
            days_diff = days_val - baseline_sched_days
            schedule_adj = (Decimal(str(days_diff)) / Decimal("365")) * Decimal("0.15")
            sim_time_prob = max(Decimal("0.02"), min(Decimal("0.98"), sim_time_prob + schedule_adj))
            direction = "extended" if days_diff > 0 else "compressed"
            assumptions.append(f"Schedule revision {direction} by {abs(days_diff)} days (total delay: {days_val} days).")

    # 9. Recompute Implementation Risk
    sim_impl = implementation_risk(tmp, source_as_of_date=as_of)
    sim_impl_score = sim_impl.score if sim_impl.score is not None else base_impl_score

    # 10. Compute Final Overall Score
    if not assumptions:
        assumptions.append("All inputs match existing baseline project values.")
        sim_rs = calculate_risk_score(base_cost_prob, base_time_prob, base_impl_score)
    else:
        sim_rs = calculate_risk_score(sim_cost_prob, sim_time_prob, sim_impl_score)

    sim_cost_score = (sim_cost_prob * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sim_time_score = (sim_time_prob * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sim_impl_score_quant = (
        sim_impl_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if sim_impl_score is not None
        else None
    )

    delta_score = (
        (sim_rs.overall_score - orig_score)
        if sim_rs.overall_score is not None and orig_score is not None
        else Decimal("0.00")
    )

    assumptions.append("Illustrative sandbox simulation: read-only, never persists.")

    return {
        "project_id": project.id,
        "project_code": project.project_code,
        "project_name": snap.project_name,
        "sector": snap.sector,
        "ministry": snap.ministry,
        "original_cost_cr": baseline_orig_cost,
        "baseline_revised_cost_cr": baseline_rev_cost,
        "baseline_expenditure_cr": baseline_exp,
        "baseline_physical_progress_pct": baseline_progress,
        "baseline_schedule_revision_days": baseline_sched_days,
        "original_overall_score": orig_score,
        "original_band": orig_band,
        "simulated_overall_score": sim_rs.overall_score,
        "simulated_band": sim_rs.band,
        "original_cost_score": orig_cost_score,
        "simulated_cost_score": sim_cost_score,
        "original_time_score": orig_time_score,
        "simulated_time_score": sim_time_score,
        "original_implementation_score": orig_impl_score,
        "simulated_implementation_score": sim_impl_score_quant,
        "delta": delta_score,
        "assumptions": assumptions,
    }
