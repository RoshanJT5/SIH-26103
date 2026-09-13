from datetime import date
from decimal import Decimal

from backend.app.models import ProjectSnapshot, RiskPrediction
from backend.app.services.risk import (
    RULE_VERSION,
    benchmark,
    build_alert,
    calculate_risk_score,
    implementation_risk,
    risk_band,
)


def snapshot(project_id: int = 1, *, progress: str = "25", revised_date: date | None = date(2026, 1, 1)) -> ProjectSnapshot:
    return ProjectSnapshot(
        id=project_id,
        project_id=project_id,
        dataset_id=1,
        source_row_number=project_id,
        project_name=f"Project {project_id}",
        sector="Roads",
        ministry="Ministry",
        implementing_agency="Agency",
        original_cost_cr=Decimal("100"),
        revised_cost_cr=Decimal("125"),
        expenditure_cr=Decimal("75"),
        physical_progress_pct=Decimal(progress),
        original_commissioning_date=date(2025, 1, 1),
        revised_commissioning_date=revised_date,
        sanction_date=date(2024, 1, 1),
        raw_values={},
        quality_flags=[],
    )


def prediction(snapshot_id: int = 1, *, band: str = "high", score: str = "70") -> RiskPrediction:
    return RiskPrediction(
        id=snapshot_id,
        snapshot_id=snapshot_id,
        cost_risk_probability=Decimal("0.60"),
        time_risk_probability=Decimal("0.70"),
        implementation_score=Decimal("50"),
        overall_score=Decimal(score),
        rule_version=RULE_VERSION,
        risk_band=band,
        availability_status="available",
    )


def test_risk_bands_are_continuous_at_boundaries():
    assert risk_band(0) == "low"
    assert risk_band(30) == "low"
    assert risk_band(Decimal("30.01")) == "medium"
    assert risk_band(60) == "medium"
    assert risk_band(Decimal("60.01")) == "high"
    assert risk_band(80) == "high"
    assert risk_band(Decimal("80.01")) == "critical"
    assert risk_band(100) == "critical"
    assert risk_band(None) is None


def test_overall_score_converts_probabilities_before_weighting():
    result = calculate_risk_score(Decimal("0.50"), Decimal("0.75"), Decimal("25"))
    assert result.overall_score == Decimal("55.00")
    assert result.band == "medium"
    assert result.availability_status == "available"


def test_missing_component_makes_overall_unavailable():
    result = calculate_risk_score(None, Decimal("0.75"), Decimal("25"))
    assert result.overall_score is None
    assert result.band is None
    assert result.availability_status == "unavailable"


def test_implementation_risk_uses_observed_indicators_only():
    result = implementation_risk(snapshot())
    assert result.score == Decimal("100.00")
    assert "low physical progress" in result.indicators
    assert "expenditure materially ahead of progress" in result.indicators
    assert "substantial schedule revision" in result.indicators


def test_alert_is_deduplicable_and_only_created_for_new_non_low_band():
    alert = build_alert(snapshot(), prediction(), indicators=("low physical progress",))
    assert alert is not None
    assert alert.severity == "high"
    assert alert.deduplication_key == "1:risk-rules-v1:high"
    assert build_alert(snapshot(), prediction(), previous_band="high") is None
    assert build_alert(snapshot(), prediction(band="low", score="20")) is None

    watch = build_alert(snapshot(), prediction(band="medium", score="40"))
    assert watch is not None
    assert watch.severity == "watch"


def test_sparse_benchmark_suppresses_percentile_and_excludes_subject():
    subject = snapshot()
    peers = [(snapshot(index), prediction(index, score=str(40 + index))) for index in range(2, 12)]
    result = benchmark(subject, peers, subject_prediction=prediction(score="70"))
    assert result.cohort_size == 10
    assert result.percentile is not None

    sparse = benchmark(subject, peers[:9])
    assert sparse.cohort_size == 9
    assert sparse.percentile is None