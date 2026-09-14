from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import ProjectSnapshot, RiskPrediction, IngestionIssue, Dataset
from ..services.features import derive_analytical_features


def build_confidence(session, snapshot, prediction):
    issues = session.scalars(
        select(IngestionIssue).where(
            IngestionIssue.dataset_id == snapshot.dataset_id,
            IngestionIssue.source_row_number == snapshot.source_row_number,
        )
    ).all()
    features = derive_analytical_features(
        snapshot, source_as_of_date=snapshot.dataset.source_as_of_date
    )
    missing = len(features.unavailable_reasons)
    total_fields = 7
    quality_score = max(
        Decimal("0"),
        (Decimal(total_fields - missing) / Decimal(total_fields) * Decimal("100")),
    ).quantize(Decimal("0.01"))
    if issues:
        quality_score = max(Decimal("0"), quality_score - Decimal("10"))
    # data_quality tiers
    if quality_score >= Decimal("80"):
        dq = "high"
    elif quality_score >= Decimal("50"):
        dq = "medium"
    else:
        dq = "low"
    # confidence: average of model probabilities if available, penalized by missing
    if (
        prediction
        and prediction.cost_risk_probability is not None
        and prediction.time_risk_probability is not None
    ):
        prob = (
            prediction.cost_risk_probability + prediction.time_risk_probability
        ) / Decimal("2")
        conf = (prob * (quality_score / Decimal("100"))).quantize(Decimal("0.0001"))
    elif prediction and prediction.overall_score is not None:
        prob = prediction.overall_score / Decimal("100")
        conf = (prob * (quality_score / Decimal("100"))).quantize(Decimal("0.0001"))
    else:
        prob = None
        conf = None
    limitations = []
    if features.unavailable_reasons:
        limitations.append(
            "Missing evidence: "
            + ", ".join(features.unavailable_reasons.keys())
            + " — shown as unavailable, never imputed as safe."
        )
    limitations.append(
        "Snapshot classification prototype; not a validated future forecast without monthly history."
    )
    if quality_score < Decimal("50"):
        limitations.append(
            "Low data quality — score should be reviewed with source records."
        )
    model_version = None
    if prediction and prediction.cost_model_version_id:
        model_version = str(prediction.cost_model_version_id)
    return {
        "probability": prob,
        "confidence": conf,
        "data_quality": dq,
        "data_quality_score": quality_score,
        "model_version": model_version,
        "rule_version": prediction.rule_version if prediction else None,
        "limitations": limitations,
        "unavailable_reasons": features.unavailable_reasons,
        "availability_status": prediction.availability_status
        if prediction
        else "unavailable",
    }
