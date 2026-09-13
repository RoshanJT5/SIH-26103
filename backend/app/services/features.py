from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Sequence

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ..models import ProjectSnapshot

FEATURE_SCHEMA_VERSION = "snapshot-features-v1"
LABEL_DEFINITION_VERSION = "snapshot-labels-v1"
TargetType = Literal["cost", "time"]

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class AnalysisDateContext:
    value: date | None
    source: Literal["request", "dataset", "unavailable"]


@dataclass(frozen=True)
class AnalyticalFeatures:
    cost_increase_cr: Decimal | None
    cost_escalation_pct: Decimal | None
    expenditure_to_original_cost_ratio: Decimal | None
    expenditure_to_revised_cost_ratio: Decimal | None
    schedule_revision_days: int | None
    project_age_days: int | None
    planned_duration_days: int | None
    analysis_date: date | None
    analysis_date_source: str
    unavailable_reasons: dict[str, str]


@dataclass(frozen=True)
class TargetLabel:
    target: TargetType
    version: str
    value: int | None
    eligible: bool
    reason: str | None


@dataclass(frozen=True)
class EligibilityCounts:
    target: TargetType
    version: str
    total: int
    eligible: int
    positive: int
    negative: int
    unknown: int


@dataclass(frozen=True)
class ModelFeatureSchema:
    target: TargetType
    version: str
    categorical: tuple[str, ...]
    numeric: tuple[str, ...]
    prohibited: frozenset[str]

    @property
    def allowed(self) -> tuple[str, ...]:
        return self.categorical + self.numeric


@dataclass(frozen=True)
class FittedPreprocessor:
    target: TargetType
    version: str
    feature_names: tuple[str, ...]
    transformer: ColumnTransformer

    def transform(self, rows: pd.DataFrame):
        missing = sorted(set(self.feature_names) - set(rows.columns))
        if missing:
            raise ValueError(f"Missing model features: {', '.join(missing)}")
        return self.transformer.transform(rows.loc[:, self.feature_names])


class LeakageFeatureError(ValueError):
    pass


IDENTIFIER_FIELDS = frozenset({"project_code", "project_name", "source_row_number"})
ANALYTICAL_FEATURE_NAMES = (
    "cost_increase_cr",
    "cost_escalation_pct",
    "expenditure_to_original_cost_ratio",
    "expenditure_to_revised_cost_ratio",
    "schedule_revision_days",
    "project_age_days",
    "planned_duration_days",
)
COMMON_CATEGORICAL = ("sector", "ministry", "implementing_agency")
COMMON_NUMERIC = (
    "original_cost_cr",
    "expenditure_cr",
    "physical_progress_pct",
    "expenditure_to_original_cost_ratio",
    "project_age_days",
    "planned_duration_days",
)

MODEL_FEATURE_SCHEMAS: dict[TargetType, ModelFeatureSchema] = {
    "cost": ModelFeatureSchema(
        target="cost",
        version=FEATURE_SCHEMA_VERSION,
        categorical=COMMON_CATEGORICAL,
        numeric=COMMON_NUMERIC,
        prohibited=IDENTIFIER_FIELDS
        | frozenset(
            {
                "revised_cost_cr",
                "cost_increase_cr",
                "cost_escalation_pct",
                "expenditure_to_revised_cost_ratio",
                "cost_overrun_label",
            }
        ),
    ),
    "time": ModelFeatureSchema(
        target="time",
        version=FEATURE_SCHEMA_VERSION,
        categorical=COMMON_CATEGORICAL,
        numeric=COMMON_NUMERIC,
        prohibited=IDENTIFIER_FIELDS
        | frozenset(
            {
                "revised_commissioning_date",
                "schedule_revision_days",
                "time_overrun_label",
            }
        ),
    ),
}

LABEL_DEFINITIONS = {
    "cost": {
        "version": LABEL_DEFINITION_VERSION,
        "positive_when": "revised_cost_cr > original_cost_cr",
        "eligibility": "original_cost_cr > 0 and revised_cost_cr > 0",
    },
    "time": {
        "version": LABEL_DEFINITION_VERSION,
        "positive_when": "revised_commissioning_date > original_commissioning_date",
        "eligibility": "both commissioning dates are present",
    },
}


def resolve_analysis_date(
    *, source_as_of_date: date | None, requested_analysis_date: date | None = None
) -> AnalysisDateContext:
    if requested_analysis_date is not None:
        return AnalysisDateContext(requested_analysis_date, "request")
    if source_as_of_date is not None:
        return AnalysisDateContext(source_as_of_date, "dataset")
    return AnalysisDateContext(None, "unavailable")


def _ratio(numerator: Decimal, denominator: Decimal | None) -> Decimal | None:
    if denominator is None or denominator <= 0:
        return None
    return (numerator / denominator).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def derive_analytical_features(
    snapshot: ProjectSnapshot,
    *,
    source_as_of_date: date | None,
    requested_analysis_date: date | None = None,
) -> AnalyticalFeatures:
    analysis = resolve_analysis_date(
        source_as_of_date=source_as_of_date,
        requested_analysis_date=requested_analysis_date,
    )
    reasons: dict[str, str] = {}

    revised_cost = snapshot.revised_cost_cr
    usable_revised_cost = revised_cost if revised_cost is not None and revised_cost > 0 else None
    if usable_revised_cost is None:
        cost_increase = None
        cost_escalation = None
        reasons["cost_increase_cr"] = "revised cost is missing or zero"
        reasons["cost_escalation_pct"] = "revised cost is missing or zero"
        reasons["expenditure_to_revised_cost_ratio"] = "revised cost is missing or zero"
    else:
        cost_increase = (usable_revised_cost - snapshot.original_cost_cr).quantize(TWO_PLACES)
        escalation_ratio = _ratio(cost_increase, snapshot.original_cost_cr)
        cost_escalation = (
            (escalation_ratio * Decimal("100")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if escalation_ratio is not None
            else None
        )

    expenditure_original_ratio = _ratio(snapshot.expenditure_cr, snapshot.original_cost_cr)
    expenditure_revised_ratio = _ratio(snapshot.expenditure_cr, usable_revised_cost)

    if snapshot.revised_commissioning_date is None:
        schedule_revision_days = None
        reasons["schedule_revision_days"] = "revised commissioning date is missing"
    else:
        schedule_revision_days = (snapshot.revised_commissioning_date - snapshot.original_commissioning_date).days

    if snapshot.sanction_date is None:
        planned_duration_days = None
        project_age_days = None
        reasons["planned_duration_days"] = "sanction date is missing"
        reasons["project_age_days"] = "sanction date is missing"
    else:
        planned_duration_days = (snapshot.original_commissioning_date - snapshot.sanction_date).days
        if planned_duration_days < 0:
            planned_duration_days = None
            reasons["planned_duration_days"] = "sanction date follows original commissioning date"

        if analysis.value is None:
            project_age_days = None
            reasons["project_age_days"] = "analysis date and dataset source date are unavailable"
        else:
            project_age_days = (analysis.value - snapshot.sanction_date).days
            if project_age_days < 0:
                project_age_days = None
                reasons["project_age_days"] = "analysis date precedes sanction date"

    return AnalyticalFeatures(
        cost_increase_cr=cost_increase,
        cost_escalation_pct=cost_escalation,
        expenditure_to_original_cost_ratio=expenditure_original_ratio,
        expenditure_to_revised_cost_ratio=expenditure_revised_ratio,
        schedule_revision_days=schedule_revision_days,
        project_age_days=project_age_days,
        planned_duration_days=planned_duration_days,
        analysis_date=analysis.value,
        analysis_date_source=analysis.source,
        unavailable_reasons=reasons,
    )


def derive_target_label(snapshot: ProjectSnapshot, target: TargetType) -> TargetLabel:
    if target == "cost":
        if snapshot.revised_cost_cr is None or snapshot.revised_cost_cr <= 0:
            return TargetLabel(target, LABEL_DEFINITION_VERSION, None, False, "revised cost is missing or zero")
        value = int(snapshot.revised_cost_cr > snapshot.original_cost_cr)
    elif target == "time":
        if snapshot.revised_commissioning_date is None:
            return TargetLabel(target, LABEL_DEFINITION_VERSION, None, False, "revised commissioning date is missing")
        value = int(snapshot.revised_commissioning_date > snapshot.original_commissioning_date)
    else:
        raise ValueError(f"Unsupported target: {target}")
    return TargetLabel(target, LABEL_DEFINITION_VERSION, value, True, None)


def count_label_eligibility(
    snapshots: Sequence[ProjectSnapshot], target: TargetType
) -> EligibilityCounts:
    labels = [derive_target_label(snapshot, target) for snapshot in snapshots]
    positive = sum(label.value == 1 for label in labels)
    negative = sum(label.value == 0 for label in labels)
    eligible = positive + negative
    return EligibilityCounts(
        target=target,
        version=LABEL_DEFINITION_VERSION,
        total=len(labels),
        eligible=eligible,
        positive=positive,
        negative=negative,
        unknown=len(labels) - eligible,
    )


def validate_model_feature_names(target: TargetType, feature_names: Sequence[str]) -> tuple[str, ...]:
    if target not in MODEL_FEATURE_SCHEMAS:
        raise ValueError(f"Unsupported target: {target}")
    selected = tuple(feature_names)
    if not selected:
        raise ValueError("At least one model feature is required.")
    if len(selected) != len(set(selected)):
        raise ValueError("Model feature names must be unique.")

    schema = MODEL_FEATURE_SCHEMAS[target]
    prohibited = sorted(set(selected) & schema.prohibited)
    unsupported = sorted(set(selected) - set(schema.allowed) - schema.prohibited)
    if prohibited:
        raise LeakageFeatureError(
            f"Prohibited {target}-target features: {', '.join(prohibited)}"
        )
    if unsupported:
        raise ValueError(f"Unsupported {target}-target features: {', '.join(unsupported)}")
    return selected


def build_model_feature_row(
    snapshot: ProjectSnapshot,
    analytical: AnalyticalFeatures,
    target: TargetType,
) -> dict[str, object]:
    schema = MODEL_FEATURE_SCHEMAS[target]
    candidates: dict[str, object] = {
        "sector": snapshot.sector,
        "ministry": snapshot.ministry,
        "implementing_agency": snapshot.implementing_agency,
        "original_cost_cr": snapshot.original_cost_cr,
        "expenditure_cr": snapshot.expenditure_cr,
        "physical_progress_pct": snapshot.physical_progress_pct,
        "expenditure_to_original_cost_ratio": analytical.expenditure_to_original_cost_ratio,
        "project_age_days": analytical.project_age_days,
        "planned_duration_days": analytical.planned_duration_days,
    }
    return {name: candidates[name] for name in schema.allowed}


def build_training_frame(
    snapshots: Sequence[ProjectSnapshot],
    target: TargetType,
    *,
    source_as_of_date: date | None,
    requested_analysis_date: date | None = None,
) -> tuple[pd.DataFrame, pd.Series, EligibilityCounts]:
    rows: list[dict[str, object]] = []
    labels: list[int] = []
    for snapshot in snapshots:
        label = derive_target_label(snapshot, target)
        if not label.eligible:
            continue
        assert label.value is not None
        analytical = derive_analytical_features(
            snapshot,
            source_as_of_date=source_as_of_date,
            requested_analysis_date=requested_analysis_date,
        )
        rows.append(build_model_feature_row(snapshot, analytical, target))
        labels.append(label.value)
    schema = MODEL_FEATURE_SCHEMAS[target]
    return (
        pd.DataFrame(rows, columns=schema.allowed),
        pd.Series(labels, name=f"{target}_overrun_label", dtype="int8"),
        count_label_eligibility(snapshots, target),
    )


def fit_model_preprocessor(
    training_rows: pd.DataFrame,
    target: TargetType,
    feature_names: Sequence[str] | None = None,
) -> FittedPreprocessor:
    schema = MODEL_FEATURE_SCHEMAS[target]
    selected = validate_model_feature_names(target, feature_names or schema.allowed)
    missing = sorted(set(selected) - set(training_rows.columns))
    if missing:
        raise ValueError(f"Missing model features: {', '.join(missing)}")

    categorical = [name for name in selected if name in schema.categorical]
    numeric = [name for name in selected if name in schema.numeric]
    transformers = []
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            )
        )
    if numeric:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )

    transformer = ColumnTransformer(transformers=transformers, remainder="drop")
    transformer.fit(training_rows.loc[:, selected])
    return FittedPreprocessor(target, schema.version, selected, transformer)
