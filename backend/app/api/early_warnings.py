from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..core.auth import get_current_user
from ..models import EarlyWarning
from ..schemas.early_warnings import (
    EarlyWarningResponse,
    EarlyWarningListResponse,
    Page,
)
from ..services.early_warning import ensure_warnings, enriched

router = APIRouter(prefix="/early-warnings", tags=["early-warnings"])


@router.get("", response_model=EarlyWarningListResponse, summary="List early warnings")
def list_warnings(
    status: str | None = Query(default=None, pattern="^(open|acknowledged|closed)$"),
    severity: str | None = Query(default=None, pattern="^(watch|high|critical)$"),
    type: str | None = None,
    project_id: int | None = None,
    dataset_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
):
    ensure_warnings(db)
    q = select(EarlyWarning).order_by(
        EarlyWarning.detected_at.desc(), EarlyWarning.id.desc()
    )
    cq = select(func.count()).select_from(EarlyWarning)
    cond = []
    if status:
        cond.append(EarlyWarning.status == status)
    if severity:
        cond.append(EarlyWarning.severity == severity)
    if type:
        cond.append(EarlyWarning.type == type)
    if project_id:
        cond.append(EarlyWarning.project_id == project_id)
    if dataset_id:
        cond.append(EarlyWarning.dataset_id == dataset_id)
    items = db.scalars(q.where(*cond).offset(offset).limit(limit)).all()
    total = db.scalar(cq.where(*cond)) or 0
    out = []
    for ew in items:
        extra = enriched(db, ew)
        out.append(
            EarlyWarningResponse.model_validate(
                {**{c.name: getattr(ew, c.name) for c in ew.__table__.columns}, **extra}
            )
        )
    return EarlyWarningListResponse(
        items=out, page=Page(offset=offset, limit=limit, total=total)
    )


@router.get("/{warning_id}", response_model=EarlyWarningResponse)
def get_warning(warning_id: int, db: Session = Depends(get_db)):
    ensure_warnings(db)
    ew = db.get(EarlyWarning, warning_id)
    if not ew:
        raise HTTPException(status_code=404, detail="Early warning not found.")
    extra = enriched(db, ew)
    return EarlyWarningResponse.model_validate(
        {**{c.name: getattr(ew, c.name) for c in ew.__table__.columns}, **extra}
    )


@router.post("/{warning_id}/acknowledge", response_model=EarlyWarningResponse)
def acknowledge(
    warning_id: int,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(get_current_user),
):
    ew = db.get(EarlyWarning, warning_id)
    if not ew:
        raise HTTPException(status_code=404, detail="Early warning not found.")
    if ew.status == "closed":
        raise HTTPException(
            status_code=422, detail="Closed warning cannot be acknowledged."
        )
    ew.status = "acknowledged"
    db.commit()
    db.refresh(ew)
    extra = enriched(db, ew)
    return EarlyWarningResponse.model_validate(
        {**{c.name: getattr(ew, c.name) for c in ew.__table__.columns}, **extra}
    )


@router.post("/{warning_id}/close", response_model=EarlyWarningResponse)
def close_warning(
    warning_id: int,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(get_current_user),
):
    ew = db.get(EarlyWarning, warning_id)
    if not ew:
        raise HTTPException(status_code=404, detail="Early warning not found.")
    ew.status = "closed"
    db.commit()
    db.refresh(ew)
    extra = enriched(db, ew)
    return EarlyWarningResponse.model_validate(
        {**{c.name: getattr(ew, c.name) for c in ew.__table__.columns}, **extra}
    )

