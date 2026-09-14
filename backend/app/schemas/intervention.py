from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel

INTERVENTION_RULES_VERSION = "intervention-v1"


class InterventionDriver(BaseModel):
    factor: str
    weight: Decimal
    contribution: Decimal
    detail: str


class DatasetRef(BaseModel):
    dataset_id: int
    source_name: str
    source_as_of_date: date | None
    imported_at: datetime


class PriorityItem(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    sector: str
    ministry: str
    implementing_agency: str
    overall_score: Decimal | None
    risk_band: str | None
    cost_risk_probability: Decimal | None
    time_risk_probability: Decimal | None
    financial_exposure_cr: Decimal | None
    progress_deviation: Decimal | None = None
    priority_score: Decimal
    rank: int
    drivers: list[InterventionDriver]
    dataset: DatasetRef | None = None


class Page(BaseModel):
    offset: int
    limit: int
    total: int


class PriorityListResponse(BaseModel):
    version: str
    formula: str
    items: list[PriorityItem]
    page: Page
