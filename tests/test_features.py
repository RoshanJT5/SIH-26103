from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from backend.app.models import ProjectSnapshot
from backend.app.services.features import (
    FEATURE_SCHEMA_VERSION,
    LABEL_DEFINITION_VERSION,
    MODEL_FEATURE_SCHEMAS,
    LeakageFeatureError,
    build_training_frame,
    count_label_eligibility,
    derive_analytical_features,
    derive_target_label,
    fit_model_preprocessor,
    resolve_analysis_date,
    validate_model_feature_names,
)


def snapshot(
    *,
    revised_cost: str | None = "150",
    revised_date: date | None = date(2025, 2, 1),
    sanction_date: date | None = date(2024, 1, 1),
) -> ProjectSnapshot:
    return ProjectSnapshot(
        project_id=1,
        dataset_id=1,
        source_row_number=1,
        project_name="Example",
        sector="Roads",
        ministry="Ministry",
        implementing_agency="Agency",
        original_cost_cr=Decimal("100"),
        revised_cost_cr=Decimal(revised_cost) if revised_cost is not None else None,
        expenditure_cr=Decimal("75"),
        physical_progress_pct=Decimal("50"),
        original_commissioning_date=date(2025, 1, 1),
        revised_commissioning_date=revised_date,
        sanction_date=sanction_date,
        raw_values={},
        quality_flags=[],
    )


def test_analytical_features_use_valid_denominators_and_explicit_date():
    result = derive_analytical_features(
        snapshot(),
        source_as_of_date=None,
        requested_analysis_date=date(2025, 1, 1),
    )

    assert result.cost_increase_cr == Decimal("50.00")
    assert result.cost_escalation_pct == Decimal("50.00")
    assert result.expenditure_to_original_cost_ratio == Decimal("0.7500")
    assert result.expenditure_to_revised_cost_ratio == Decimal("0.5000")
    assert result.schedule_revision_days == 31
    assert result.project_age_days == 366
    assert result.planned_duration_days == 366
    assert result.analysis_date_source == "request"


@pytest.mark.parametrize("revised_cost", [None, "0"])
def test_missing_or_zero_revised_cost_produces_unknown_derived_values(revised_cost):
    result = derive_analytical_features(
        snapshot(revised_cost=revised_cost),
        source_as_of_date=None,
    )

    assert result.cost_increase_cr is None
    assert result.cost_escalation_pct is None
    assert result.expenditure_to_revised_cost_ratio is None
    assert result.project_age_days is None
    assert result.analysis_date_source == "unavailable"
    assert "analysis date" in result.unavailable_reasons["project_age_days"]


def test_dataset_source_date_is_used_but_never_invented():
    selected = resolve_analysis_date(source_as_of_date=date(2026, 9, 1))
    unavailable = resolve_analysis_date(source_as_of_date=None)

    assert selected.value == date(2026, 9, 1)
    assert selected.source == "dataset"
    assert unavailable.value is None
    assert unavailable.source == "unavailable"


def test_versioned_cost_and_time_labels_keep_unknown_targets_out():
    later = snapshot()
    equal = snapshot(revised_cost="100", revised_date=date(2025, 1, 1))
    unknown = snapshot(revised_cost="0", revised_date=None)

    assert derive_target_label(later, "cost").value == 1
    assert derive_target_label(equal, "cost").value == 0
    assert derive_target_label(unknown, "cost").eligible is False
    assert derive_target_label(unknown, "time").value is None

    cost_counts = count_label_eligibility([later, equal, unknown], "cost")
    time_counts = count_label_eligibility([later, equal, unknown], "time")
    assert cost_counts.version == LABEL_DEFINITION_VERSION
    assert (cost_counts.total, cost_counts.eligible, cost_counts.positive, cost_counts.negative, cost_counts.unknown) == (3, 2, 1, 1, 1)
    assert (time_counts.total, time_counts.eligible, time_counts.positive, time_counts.negative, time_counts.unknown) == (3, 2, 1, 1, 1)


def test_model_schemas_reject_leakage_and_identifiers():
    with pytest.raises(LeakageFeatureError):
        validate_model_feature_names("cost", ["sector", "revised_cost_cr"])
    with pytest.raises(LeakageFeatureError):
        validate_model_feature_names("cost", ["project_code"])
    with pytest.raises(LeakageFeatureError):
        validate_model_feature_names("time", ["physical_progress_pct", "schedule_revision_days"])
    with pytest.raises(LeakageFeatureError):
        validate_model_feature_names("time", ["revised_commissioning_date"])

    assert MODEL_FEATURE_SCHEMAS["cost"].version == FEATURE_SCHEMA_VERSION
    assert "revised_cost_cr" not in MODEL_FEATURE_SCHEMAS["cost"].allowed
    assert "revised_commissioning_date" not in MODEL_FEATURE_SCHEMAS["time"].allowed


def test_preprocessor_is_fitted_only_from_selected_training_features():
    training = pd.DataFrame(
        [
            {
                "sector": "Roads",
                "ministry": "M1",
                "implementing_agency": "A1",
                "original_cost_cr": 100,
                "expenditure_cr": 25,
                "physical_progress_pct": 30,
                "expenditure_to_original_cost_ratio": 0.25,
                "project_age_days": 100,
                "planned_duration_days": 500,
                "revised_cost_cr": 999,
            },
            {
                "sector": "Energy",
                "ministry": "M2",
                "implementing_agency": "A2",
                "original_cost_cr": 200,
                "expenditure_cr": None,
                "physical_progress_pct": 60,
                "expenditure_to_original_cost_ratio": None,
                "project_age_days": 200,
                "planned_duration_days": 700,
                "revised_cost_cr": 999,
            },
        ]
    )
    fitted = fit_model_preprocessor(training, "cost")
    transformed = fitted.transform(training)

    assert "revised_cost_cr" not in fitted.feature_names
    assert transformed.shape[0] == 2
    assert transformed.shape[1] > len(fitted.feature_names)

    with pytest.raises(LeakageFeatureError):
        fit_model_preprocessor(training, "cost", ["sector", "revised_cost_cr"])


def test_training_frame_excludes_unknown_labels_and_prohibited_fields():
    eligible = snapshot()
    unknown = snapshot(revised_cost="0", revised_date=None)

    cost_frame, cost_labels, cost_counts = build_training_frame(
        [eligible, unknown],
        "cost",
        source_as_of_date=date(2025, 1, 1),
    )
    time_frame, time_labels, time_counts = build_training_frame(
        [eligible, unknown],
        "time",
        source_as_of_date=date(2025, 1, 1),
    )

    assert len(cost_frame) == len(cost_labels) == cost_counts.eligible == 1
    assert len(time_frame) == len(time_labels) == time_counts.eligible == 1
    assert "project_code" not in cost_frame.columns
    assert "revised_cost_cr" not in cost_frame.columns
    assert "revised_commissioning_date" not in time_frame.columns
    assert "schedule_revision_days" not in time_frame.columns
