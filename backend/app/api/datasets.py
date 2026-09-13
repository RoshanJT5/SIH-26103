from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models import Dataset, IngestionIssue
from ..schemas.uploads import DatasetQualityResponse, IngestionIssueResponse, QualitySummary

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/{dataset_id}/quality", response_model=DatasetQualityResponse)
def get_dataset_quality(
    dataset_id: int,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    db: Session = Depends(get_db),
) -> DatasetQualityResponse:
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "completed"))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Completed dataset not found.")

    summary_rows = db.execute(
        select(IngestionIssue.severity, IngestionIssue.issue_code, func.count(IngestionIssue.id))
        .where(IngestionIssue.dataset_id == dataset_id)
        .group_by(IngestionIssue.severity, IngestionIssue.issue_code)
        .order_by(IngestionIssue.severity, IngestionIssue.issue_code)
    ).all()
    issue_count = db.scalar(
        select(func.count()).select_from(IngestionIssue).where(IngestionIssue.dataset_id == dataset_id)
    ) or 0
    issue_rows = db.scalars(
        select(IngestionIssue)
        .where(IngestionIssue.dataset_id == dataset_id)
        .order_by(IngestionIssue.source_row_number, IngestionIssue.id)
        .offset(offset)
        .limit(limit)
    ).all()

    return DatasetQualityResponse(
        dataset_id=dataset.id,
        source_name=dataset.source_name,
        status=dataset.status,
        accepted_count=dataset.accepted_count,
        rejected_count=dataset.rejected_count,
        issue_count=issue_count,
        offset=offset,
        limit=limit,
        summary=[QualitySummary(severity=row[0], issue_code=row[1], count=row[2]) for row in summary_rows],
        issues=[IngestionIssueResponse.model_validate(issue) for issue in issue_rows],
    )
