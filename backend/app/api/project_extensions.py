from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..db.session import get_db
from ..models import ProjectSnapshot, Dataset, RiskPrediction
from ..schemas.confidence import ConfidenceResponse
from ..schemas.trajectory import ProgressTrajectoryResponse
from ..schemas.forecast import ForecastResponse
from ..schemas.recommendations import RecommendationsResponse
from ..schemas.simulation import SimulationInput, SimulationResult
from ..schemas.reporting import ReportResponse
from ..services.confidence import build_confidence
from ..services.trajectory import build_trajectory
from ..services.forecast import build_forecast
from ..services.simulation import simulate
from ..services.recommendations import build_recommendations
from ..services.reporting import build_report

router = APIRouter(tags=["projects"])


def _latest(session, sid):
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == sid)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


@router.get("/risk/projects/{project_id}/confidence", response_model=ConfidenceResponse)
def confidence(project_id: int, db: Session = Depends(get_db)):
    snap = db.scalar(
        select(ProjectSnapshot)
        .join(Dataset)
        .where(ProjectSnapshot.project_id == project_id, Dataset.status == "completed")
        .order_by(ProjectSnapshot.id.desc())
    )
    if not snap:
        raise HTTPException(status_code=404, detail="Project not found.")
    pred = _latest(db, snap.id)
    data = build_confidence(db, snap, pred)
    return ConfidenceResponse(
        project_id=project_id,
        snapshot_id=snap.id,
        prediction_id=pred.id if pred else None,
        **data,
    )


@router.get(
    "/projects/{project_id}/progress-trajectory",
    response_model=ProgressTrajectoryResponse,
)
def progress_trajectory(project_id: int, db: Session = Depends(get_db)):
    pts = build_trajectory(db, project_id)
    if pts is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    snap = db.scalar(
        select(ProjectSnapshot).where(ProjectSnapshot.project_id == project_id).limit(1)
    )
    code = snap.project.project_code if snap else str(project_id)
    unavailable = None
    if all(p["expected_progress"] is None for p in pts):
        unavailable = "Expected progress unavailable: sanction date or planned duration missing, or analysis date unavailable."
    return ProgressTrajectoryResponse(
        project_id=project_id,
        project_code=code,
        methodology="expected = project_age / planned_duration *100; deviation = actual - expected",
        expected_method="linear schedule assumption",
        points=pts,
        unavailable_reason=unavailable,
    )


@router.get("/risk/projects/{project_id}/forecast", response_model=ForecastResponse)
def forecast(project_id: int, horizon: int = 3, db: Session = Depends(get_db)):
    res = build_forecast(db, project_id, horizon=horizon)
    if not res:
        raise HTTPException(status_code=404, detail="Project not found.")
    points, methodology, limitations = res
    snap = db.scalar(
        select(ProjectSnapshot).where(ProjectSnapshot.project_id == project_id).limit(1)
    )
    code = snap.project.project_code if snap else str(project_id)
    return ForecastResponse(
        project_id=project_id,
        project_code=code,
        methodology=methodology,
        limitations=limitations,
        points=points,
    )


@router.post("/simulation/project", response_model=SimulationResult)
def sim(body: SimulationInput, db: Session = Depends(get_db)):
    res = simulate(
        db,
        body.project_id,
        revised_cost_cr=body.revised_cost_cr,
        expenditure_cr=body.expenditure_cr,
        physical_progress_pct=body.physical_progress_pct,
        schedule_revision_days=body.schedule_revision_days,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Project not found.")
    return SimulationResult(**res)


@router.get(
    "/projects/{project_id}/recommendations", response_model=RecommendationsResponse
)
def recommendations(project_id: int, db: Session = Depends(get_db)):
    res = build_recommendations(db, project_id)
    if not res:
        raise HTTPException(status_code=404, detail="Project not found.")
    return RecommendationsResponse(
        project_id=project_id,
        project_code=res["project_code"],
        methodology=res["methodology"],
        items=res["items"],
        limitations=res["limitations"],
    )


@router.post("/reports/project-brief", response_model=ReportResponse)
def report(body: dict, db: Session = Depends(get_db)):
    pid = body.get("project_id")
    if not pid:
        raise HTTPException(status_code=422, detail="project_id required")
    res = build_report(db, int(pid))
    if not res:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ReportResponse(**res)
