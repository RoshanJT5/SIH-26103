from decimal import Decimal
from datetime import date
from pydantic import BaseModel


class TrajectoryPoint(BaseModel):
    dataset_id: int
    source_as_of_date: date | None
    expected_progress: Decimal | None
    actual_progress: Decimal
    deviation: Decimal | None
    snapshot_id: int


class ProgressTrajectoryResponse(BaseModel):
    project_id: int
    project_code: str
    methodology: str
    expected_method: str
    points: list[TrajectoryPoint]
    unavailable_reason: str | None = None
