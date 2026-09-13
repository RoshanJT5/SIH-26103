from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Alert, ProjectSnapshot, RiskPrediction
from .features import derive_analytical_features

RULE_VERSION = "risk-rules-v1"
MINIMUM_BENCHMARK_PEERS = 10
_HUNDRED = Decimal("100")
_TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class ImplementationRisk:
    score: Decimal | None
    indicators: tuple[str, ...]
    missing_indicators: tuple[str, ...]


@dataclass(frozen=True)
class RiskScore:
    cost_score: Decimal | None
    time_score: Decimal | None
    implementation_score: Decimal | None
    overall_score: Decimal | None
    band: str | None
    availability_status: str


@dataclass(frozen=True)
class BenchmarkResult:
    cohort_size: int
    percentile: Decimal | None
    average_cost_escalation_pct: Decimal | None
    average_expenditure_ratio: Decimal | None
    average_progress_pct: Decimal | None
    average_risk_score: Decimal | None


def implementation_risk(
    snapshot: ProjectSnapshot,
    *,
    source_as_of_date: date | None = None,
    analysis_date: date | None = None,
) -> ImplementationRisk:
    features = derive_analytical_features(
        snapshot,
        source_as_of_date=source_as_of_date,
        requested_analysis_date=analysis_date,
    )
    points = Decimal("0")
    available_weight = Decimal("0")
    indicators: list[str] = []
    missing: list[str] = []

    progress = snapshot.physical_progress_pct
    if progress is None:
        missing.append("physical_progress_pct")
    else:
        available_weight += Decimal("40")
        if progress <= 25:
            points += Decimal("40")
            indicators.append("low physical progress")
        elif progress <= 50:
            points += Decimal("20")
            indicators.append("moderate physical progress")

    expenditure_ratio = features.expenditure_to_original_cost_ratio
    if expenditure_ratio is None:
        missing.append("expenditure_to_original_cost_ratio")
    else:
        available_weight += Decimal("35")
        mismatch = expenditure_ratio - (progress / _HUNDRED)
        if mismatch >= Decimal("0.25"):
            points += Decimal("35")
            indicators.append("expenditure materially ahead of progress")
        elif mismatch >= Decimal("0.10"):
            points += Decimal("17.5")
            indicators.append("expenditure ahead of progress")

    schedule_days = features.schedule_revision_days
    if schedule_days is None:
        missing.append("schedule_revision_days")
    else:
        available_weight += Decimal("25")
        if schedule_days >= 365:
            points += Decimal("25")
            indicators.append("substantial schedule revision")
        elif schedule_days >= 180:
            points += Decimal("17.5")
            indicators.append("material schedule revision")
        elif schedule_days >= 90:
            points += Decimal("10")
            indicators.append("schedule revision")

    if available_weight == 0:
        score = None
    else:
        score = (points * _HUNDRED / available_weight).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    return ImplementationRisk(score, tuple(indicators), tuple(missing))


def risk_band(score: Decimal | float | int | None) -> str | None:
    if score is None:
        return None
    value = Decimal(str(score))
    if not Decimal("0") <= value <= _HUNDRED:
        raise ValueError("Risk score must be between 0 and 100")
    if value <= 30:
        return "low"
    if value <= 60:
        return "medium"
    if value <= 80:
        return "high"
    return "critical"


def calculate_risk_score(
    cost_probability: Decimal | float | None,
    time_probability: Decimal | float | None,
    implementation_score: Decimal | float | None,
) -> RiskScore:
    cost_score = None if cost_probability is None else Decimal(str(cost_probability)) * _HUNDRED
    time_score = None if time_probability is None else Decimal(str(time_probability)) * _HUNDRED
    implementation = None if implementation_score is None else Decimal(str(implementation_score))
    components = (cost_score, time_score, implementation)
    if any(component is None for component in components):
        return RiskScore(cost_score, time_score, implementation, None, None, "unavailable")
    overall = (
        Decimal("0.40") * cost_score
        + Decimal("0.40") * time_score
        + Decimal("0.20") * implementation
    ).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)
    return RiskScore(cost_score, time_score, implementation, overall, risk_band(overall), "available")


def monitoring_focus(score: RiskScore, indicators: Iterable[str] = ()) -> str:
    signals = list(indicators)
    if not signals:
        if score.band in {"high", "critical"}:
            return "Prioritize a detailed implementation review."
        return "Continue routine monitoring."
    return "Review " + "; ".join(signals) + "."


def build_alert(
    snapshot: ProjectSnapshot,
    prediction: RiskPrediction,
    *,
    indicators: Iterable[str] = (),
    previous_band: str | None = None,
) -> Alert | None:
    if prediction.risk_band is None or prediction.risk_band == "low":
        return None
    band_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if previous_band is not None and band_order.get(prediction.risk_band, 0) <= band_order.get(previous_band, 0):
        return None
    alert_severity = "watch" if prediction.risk_band == "medium" else prediction.risk_band
    score = RiskScore(
        None if prediction.cost_risk_probability is None else prediction.cost_risk_probability * _HUNDRED,
        None if prediction.time_risk_probability is None else prediction.time_risk_probability * _HUNDRED,
        prediction.implementation_score,
        prediction.overall_score,
        prediction.risk_band,
        prediction.availability_status,
    )
    return Alert(
        snapshot_id=snapshot.id,
        prediction_id=prediction.id,
        rule_version=prediction.rule_version,
        severity=alert_severity,
        message=monitoring_focus(score, indicators),
        deduplication_key=f"{snapshot.id}:{prediction.rule_version}:{prediction.risk_band}",
    )


def persist_alert(session: Session, alert: Alert | None) -> Alert | None:
    if alert is None:
        return None
    existing = session.scalar(
        select(Alert).where(Alert.deduplication_key == alert.deduplication_key)
    )
    if existing is not None:
        return existing
    session.add(alert)
    session.flush()
    return alert


def benchmark(
    subject: ProjectSnapshot,
    peers: Iterable[tuple[ProjectSnapshot, RiskPrediction]],
    *,
    subject_prediction: RiskPrediction | None = None,
    minimum_peers: int = MINIMUM_BENCHMARK_PEERS,
) -> BenchmarkResult:
    comparable = [
        (peer, prediction)
        for peer, prediction in peers
        if peer.id != subject.id
        and peer.sector == subject.sector
        and peer.ministry == subject.ministry
        and subject.original_cost_cr * Decimal("0.5")
        <= peer.original_cost_cr
        <= subject.original_cost_cr * Decimal("1.5")
    ]
    if len(comparable) < minimum_peers:
        return BenchmarkResult(len(comparable), None, None, None, None, None)

    subject_score = None if subject_prediction is None else subject_prediction.overall_score
    scores = [prediction.overall_score for peer, prediction in comparable if prediction.overall_score is not None]
    percentile = None
    if subject_score is not None and scores:
        percentile = (Decimal(sum(score <= subject_score for score in scores)) / Decimal(len(scores)) * _HUNDRED).quantize(_TWO_PLACES)

    cost_escalations = []
    expenditure_ratios = []
    progress_values = []
    for peer, peer_prediction in comparable:
        features = derive_analytical_features(peer, source_as_of_date=None)
        if features.cost_escalation_pct is not None:
            cost_escalations.append(float(features.cost_escalation_pct))
        if features.expenditure_to_original_cost_ratio is not None:
            expenditure_ratios.append(float(features.expenditure_to_original_cost_ratio))
        progress_values.append(float(peer.physical_progress_pct))

    average = lambda values: None if not values else Decimal(str(mean(values))).quantize(_TWO_PLACES)
    return BenchmarkResult(
        len(comparable),
        percentile,
        average(cost_escalations),
        average(expenditure_ratios),
        average(progress_values),
        average([float(score) for score in scores]),
    )