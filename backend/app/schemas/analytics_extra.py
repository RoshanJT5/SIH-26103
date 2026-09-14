from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel


class CostDriver(BaseModel):
    feature: str
    average_shap: Decimal
    coverage: int
    interpretation: str


class MinistryHealth(BaseModel):
    ministry: str
    project_count: int
    average_overall_score: Decimal | None
    high_risk_projects: int
    critical_projects: int
    band_distribution: dict[str, int]
    methodology: str
    limitations: list[str]


class GeographyItem(BaseModel):
    region: str
    project_count: int
    average_overall_score: Decimal | None
    high_risk_projects: int


class TimelinePoint(BaseModel):
    dataset_id: int
    source_as_of_date: date | None
    snapshot_id: int
    overall_score: Decimal | None
    risk_band: str | None
    physical_progress_pct: Decimal
    expenditure_cr: Decimal


class ModelInfo(BaseModel):
    id: int
    name: str
    target_type: str
    feature_schema: dict
    metrics: dict
    created_at: datetime
    training_dataset_id: int


class ModelPerformance(BaseModel):
    target_type: str
    latest_metrics: dict
    comparison: list[dict]
    note: str
