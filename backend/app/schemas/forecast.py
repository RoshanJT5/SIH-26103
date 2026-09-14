from decimal import Decimal
from datetime import date
from pydantic import BaseModel


class ForecastPoint(BaseModel):
    dataset_id: int | None = None
    source_as_of_date: date | None
    overall_score: Decimal | None
    is_forecast: bool
    method: str


class ForecastResponse(BaseModel):
    project_id: int
    project_code: str
    methodology: str
    limitations: list[str]
    points: list[ForecastPoint]
