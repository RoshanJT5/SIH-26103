from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..models.updates import PlatformUpdate
from ..schemas.updates import UpdateItem, UpdateListResponse

router = APIRouter(prefix="/updates", tags=["updates"])


def _to_item(row: PlatformUpdate) -> UpdateItem:
    return UpdateItem(
        id=row.id,
        category=row.category,
        title=row.title,
        summary=row.summary,
        content=row.content,
        published_at=row.published_at,
        updated_at=row.updated_at,
        status=row.status,
        related_dataset_id=row.related_dataset_id,
        meta=row.meta,
    )


@router.get(
    "",
    response_model=UpdateListResponse,
    summary="List platform updates",
    description="Returns platform updates newest first, filterable by category and search term.",
)
def list_updates(
    category: str | None = Query(
        default=None,
        description="Filter by category: dataset, monitoring, model, methodology, platform",
    ),
    search: str | None = Query(default=None, description="Search in title and summary"),
    date_from: str | None = Query(
        default=None, description="ISO date lower bound (published_at)"
    ),
    date_to: str | None = Query(
        default=None, description="ISO date upper bound (published_at)"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> UpdateListResponse:
    query = select(PlatformUpdate).where(PlatformUpdate.status == "published")
    count_q = (
        select(func.count())
        .select_from(PlatformUpdate)
        .where(PlatformUpdate.status == "published")
    )
    conditions = []
    if category:
        conditions.append(PlatformUpdate.category == category)
    if search:
        like = f"%{search}%"
        conditions.append(
            (PlatformUpdate.title.ilike(like)) | (PlatformUpdate.summary.ilike(like))
        )
    if date_from:
        conditions.append(PlatformUpdate.published_at >= date_from)
    if date_to:
        conditions.append(PlatformUpdate.published_at <= date_to)
    if conditions:
        query = query.where(*conditions)
        count_q = count_q.where(*conditions)
    total = db.scalar(count_q) or 0
    rows = db.scalars(
        query.order_by(PlatformUpdate.published_at.desc()).offset(offset).limit(limit)
    ).all()
    return UpdateListResponse(
        items=[_to_item(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.get(
    "/{update_id}",
    response_model=UpdateItem,
    summary="Get update detail",
    description="Returns a single platform update by id.",
)
def get_update(update_id: int, db: Session = Depends(get_db)) -> UpdateItem:
    row = db.get(PlatformUpdate, update_id)
    if row is None or row.status != "published":
        raise HTTPException(status_code=404, detail="Update not found.")
    return _to_item(row)
