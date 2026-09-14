from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel

RISK_TREND_RULES_VERSION = "risk-trends-v1"
THRESHOLDS_DOC = "improving: change <= -5, stable: -5 < change <= 5, watch: 5 < change <= 10, deteriorating: 10 < change <= 20, rapid_deterioration: change > 20"


class TrendPoint(BaseModel):
    dataset_id: int
    source_name: str
    source_as_of_date: date | None
    imported_at: datetime
    snapshot_id: int
    overall_score: Decimal | None
    risk_band: str | None
    cost_risk_probability: Decimal | None = None
    time_risk_probability: Decimal | None = None


class TrendItem(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    sector: str
    ministry: str
    implementing_agency: str
    history: list[TrendPoint]
    first_score: Decimal | None
    last_score: Decimal | None
    score_change: Decimal | None
    trend: str
    trend_label: str


class Page(BaseModel):
    offset: int
    limit: int
    total: int


class RiskTrendsResponse(BaseModel):
    version: str
    thresholds: dict[str, str]
    items: list[TrendItem]
    page: Page
