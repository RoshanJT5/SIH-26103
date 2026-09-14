from decimal import Decimal
from pydantic import BaseModel


class ConfidenceResponse(BaseModel):
    project_id: int
    snapshot_id: int
    prediction_id: int | None
    probability: Decimal | None = None
    confidence: Decimal | None = None
    data_quality: str
    data_quality_score: Decimal | None
    model_version: str | None
    rule_version: str | None
    limitations: list[str]
    unavailable_reasons: dict[str, str]
    availability_status: str
