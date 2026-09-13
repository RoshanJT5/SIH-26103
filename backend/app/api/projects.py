from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.auth import get_admin_user
from ..db.session import get_db
from ..schemas.uploads import UploadValidationResponse
from ..services.csv_upload import CsvUploadError, validate_project_csv
from ..services.ingestion import persist_validated_import

router = APIRouter(prefix="/projects", tags=["projects"])

ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
}


@router.post("/upload", response_model=UploadValidationResponse, status_code=status.HTTP_200_OK)
async def upload_project_csv(
    file: Annotated[UploadFile, File()],
    source_as_of_date: Annotated[date | None, Form()] = None,
    db: Session = Depends(get_db),
    _admin_user: str = Depends(get_admin_user),
) -> UploadValidationResponse:
    settings = get_settings()
    filename = Path(file.filename or "").name

    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only .csv project reports are accepted.")
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported CSV content type: {file.content_type}.")

    content = await file.read(settings.max_upload_bytes + 1)
    await file.close()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"CSV exceeds the {settings.max_upload_bytes}-byte upload limit.",
        )

    try:
        parsed = validate_project_csv(content)
    except CsvUploadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    checksum = sha256(content).hexdigest()
    persisted = persist_validated_import(
        db,
        parsed=parsed,
        source_name=filename,
        checksum=checksum,
        source_as_of_date=source_as_of_date,
    )
    dataset = persisted.dataset

    return UploadValidationResponse(
        dataset_id=dataset.id,
        filename=filename,
        size_bytes=len(content),
        status=dataset.status,
        idempotent=not persisted.created,
        checksum=checksum,
        source_as_of_date=dataset.source_as_of_date,
        imported_at=dataset.imported_at,
        preamble_rows=parsed.structure.preamble_rows,
        record_count=parsed.structure.record_count,
        accepted_count=dataset.accepted_count,
        rejected_count=dataset.rejected_count,
        issue_count=persisted.issue_count,
        source_columns=parsed.structure.source_columns,
        canonical_columns=parsed.structure.canonical_columns,
    )

