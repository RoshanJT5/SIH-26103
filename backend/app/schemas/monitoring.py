from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class DatasetFreshness(BaseModel):
    dataset_id: int
    source_name: str
    source_as_of_date: date | None
    imported_at: datetime


class RiskFields(BaseModel):
    prediction_id: int | None = None
    cost_risk_probability: Decimal | None = None
    time_risk_probability: Decimal | None = None
    implementation_score: Decimal | None = None
    overall_score: Decimal | None = None
    risk_band: str | None = None
    availability_status: str = "unavailable"
    rule_version: str | None = None
    predicted_at: datetime | None = None


class ProjectSummary(RiskFields):
    project_id: int
    project_code: str
    snapshot_id: int
    project_name: str
    sector: str
    ministry: str
    implementing_agency: str
    original_cost_cr: Decimal
    revised_cost_cr: Decimal | None
    expenditure_cr: Decimal
    physical_progress_pct: Decimal
    dataset: DatasetFreshness


class ProjectDetail(ProjectSummary):
    original_commissioning_date: date
    revised_commissioning_date: date | None
    sanction_date: date | None
    cost_increase_cr: Decimal | None
    cost_escalation_pct: Decimal | None
    expenditure_to_original_cost_ratio: Decimal | None
    expenditure_to_revised_cost_ratio: Decimal | None
    schedule_revision_days: int | None
    project_age_days: int | None
    planned_duration_days: int | None
    analysis_date_source: str
    unavailable_reasons: dict[str, str]


class Page(BaseModel):
    offset: int
    limit: int
    total: int


class ProjectListResponse(BaseModel):
    items: list[ProjectSummary]
    page: Page
    dataset: DatasetFreshness | None


class DashboardSummary(BaseModel):
    total_projects: int
    available_predictions: int
    high_risk_projects: int
    critical_projects: int
    average_overall_score: Decimal | None
    total_original_cost_cr: Decimal
    total_revised_cost_cr: Decimal
    total_expenditure_cr: Decimal
    dataset: DatasetFreshness | None


class GroupAnalytics(BaseModel):
    group: str
    project_count: int
    available_prediction_count: int
    average_overall_score: Decimal | None
    high_risk_projects: int
    critical_projects: int


class BenchmarkResponse(BaseModel):
    project_id: int
    cohort_size: int
    percentile: Decimal | None
    average_cost_escalation_pct: Decimal | None
    average_expenditure_ratio: Decimal | None
    average_progress_pct: Decimal | None
    average_risk_score: Decimal | None


class RiskExplanationResponse(BaseModel):
    prediction_id: int
    project_id: int
    rule_version: str
    overall_score: Decimal | None
    risk_band: str | None
    explanations: list["RiskExplanationItem"]


class RiskExplanationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component_model_version_id: int
    feature_name: str
    feature_value: object | None
    shap_contribution: Decimal
    baseline_value: Decimal
    output_scale: str


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    snapshot_id: int
    prediction_id: int
    rule_version: str
    severity: str
    message: str
    status: str
    deduplication_key: str
    created_at: datetime


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    page: Page