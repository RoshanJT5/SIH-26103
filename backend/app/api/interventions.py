from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..models import ProjectSnapshot, Dataset
from ..schemas.intervention import (
    PriorityListResponse,
    PriorityItem,
    DatasetRef,
    Page,
    INTERVENTION_RULES_VERSION,
)
from ..services.intervention import list_priorities, compute_priority, FORMULA, VERSION

router = APIRouter(prefix="/interventions", tags=["interventions"])


def _ref(ds):
    return DatasetRef(
        dataset_id=ds.id,
        source_name=ds.source_name,
        source_as_of_date=ds.source_as_of_date,
        imported_at=ds.imported_at,
    )


@router.get(
    "/priority",
    response_model=PriorityListResponse,
    summary="Intervention priority queue",
    description="Transparent weighted priority. Formula priority = 0.35*overall_score + 0.15*max(0,score_change) + 0.15*cost_prob*100 + 0.15*time_prob*100 + 0.10*financial_exposure_norm + 0.10*progress_deviation*100. Version intervention-v1.",
)
def priority_list(
    sector: str | None = None,
    ministry: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
):
    items, total = list_priorities(
        db, limit=limit, offset=offset, sector=sector, ministry=ministry
    )
    out = []
    for it in items:
        s = it["snapshot"]
        pred = it["pred"]
        out.append(
            PriorityItem(
                project_id=s.project_id,
                project_code=s.project.project_code,
                project_name=s.project_name,
                sector=s.sector,
                ministry=s.ministry,
                implementing_agency=s.implementing_agency,
                overall_score=pred.overall_score if pred else None,
                risk_band=pred.risk_band if pred else None,
                cost_risk_probability=pred.cost_risk_probability if pred else None,
                time_risk_probability=pred.time_risk_probability if pred else None,
                financial_exposure_cr=s.revised_cost_cr or s.original_cost_cr,
                progress_deviation=None,
                priority_score=it["priority"],
                rank=it["rank"],
                drivers=it["drivers"],
                dataset=_ref(s.dataset),
            )
        )
    return PriorityListResponse(
        version=VERSION,
        formula=FORMULA,
        items=out,
        page=Page(offset=offset, limit=limit, total=total),
    )


@router.get(
    "/priority/{project_id}",
    response_model=PriorityItem,
    summary="Single project priority",
)
def priority_one(project_id: int, db: Session = Depends(get_db)):
    snap = db.scalar(
        select(ProjectSnapshot)
        .join(ProjectSnapshot.project)
        .join(ProjectSnapshot.dataset)
        .where(ProjectSnapshot.project_id == project_id, Dataset.status == "completed")
        .order_by(ProjectSnapshot.id.desc())
    )
    if not snap:
        raise HTTPException(status_code=404, detail="Project not found.")
    priority, drivers, pred = compute_priority(db, snap)
    items, total = list_priorities(db, limit=500, offset=0)
    rank = next(
        (it["rank"] for it in items if it["snapshot"].project_id == project_id), 1
    )
    return PriorityItem(
        project_id=snap.project_id,
        project_code=snap.project.project_code,
        project_name=snap.project_name,
        sector=snap.sector,
        ministry=snap.ministry,
        implementing_agency=snap.implementing_agency,
        overall_score=pred.overall_score if pred else None,
        risk_band=pred.risk_band if pred else None,
        cost_risk_probability=pred.cost_risk_probability if pred else None,
        time_risk_probability=pred.time_risk_probability if pred else None,
        financial_exposure_cr=snap.revised_cost_cr or snap.original_cost_cr,
        progress_deviation=None,
        priority_score=priority,
        rank=rank,
        drivers=drivers,
        dataset=_ref(snap.dataset),
    )
