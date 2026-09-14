from datetime import datetime, date
from typing import Any
from pydantic import BaseModel, ConfigDict


class EarlyWarningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    dataset_id: int
    snapshot_id: int
    prediction_id: int | None
    type: str
    severity: str
    title: str
    description: str
    evidence: dict[str, Any] | None
    recommended_review: str
    status: str
    deduplication_key: str
    detected_at: datetime
    data_date: datetime | None
    project_code: str | None = None
    project_name: str | None = None
    sector: str | None = None
    ministry: str | None = None


class EarlyWarningListResponse(BaseModel):
    items: list[EarlyWarningResponse]
    page: "Page"
    version: str = "early-warning-v1"


class Page(BaseModel):
    offset: int
    limit: int
    total: int
