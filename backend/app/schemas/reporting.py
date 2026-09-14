from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel


class ReportSection(BaseModel):
    title: str
    body: str


class ReportResponse(BaseModel):
    project_id: int
    project_code: str
    project_name: str
    generated_at: datetime
    dataset: dict | None
    overall_score: Decimal | None
    risk_band: str | None
    sections: list[ReportSection]
    limitations: list[str]
