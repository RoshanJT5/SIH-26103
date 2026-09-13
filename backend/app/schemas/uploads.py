from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class UploadValidationResponse(BaseModel):
    dataset_id: int
    filename: str
    size_bytes: int
    status: str
    idempotent: bool
    checksum: str
    source_as_of_date: date | None
    imported_at: datetime
    preamble_rows: int
    record_count: int
    accepted_count: int
    rejected_count: int
    issue_count: int
    source_columns: list[str]
    canonical_columns: list[str]


class QualitySummary(BaseModel):
    severity: str
    issue_code: str
    count: int


class IngestionIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_row_number: int
    field: str | None
    raw_value: str | None
    issue_code: str
    severity: str
    message: str | None


class DatasetQualityResponse(BaseModel):
    dataset_id: int
    source_name: str
    status: str
    accepted_count: int
    rejected_count: int
    issue_count: int
    offset: int
    limit: int
    summary: list[QualitySummary]
    issues: list[IngestionIssueResponse]
