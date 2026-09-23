from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from ..db.session import get_db
from ..services.prediction_loader import (
    get_latest_predictions_map,
    get_cached,
    set_cached,
)
from ..models import (
    Alert,
    Dataset,
    Project,
    ProjectSnapshot,
    RiskExplanation,
    RiskPrediction,
)
from ..schemas.monitoring import (
    AlertListResponse,
    AlertResponse,
    BenchmarkResponse,
    DashboardSummary,
    DatasetFreshness,
    GroupAnalytics,
    Page,
    ProjectDetail,
    ProjectListResponse,
    ProjectSummary,
    RiskExplanationItem,
    RiskExplanationResponse,
    RiskFields,
    SnapshotComparisonResponse,
)
from ..services.features import derive_analytical_features
from ..services.risk import benchmark
from ..services.snapshot_comparison import compare_snapshots

router = APIRouter(tags=["monitoring"])
MAX_LIMIT = 500


def _latest_prediction(session: Session, snapshot_id: int) -> RiskPrediction | None:
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == snapshot_id)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


def _freshness(dataset: Dataset) -> DatasetFreshness:
    return DatasetFreshness(
        dataset_id=dataset.id,
        source_name=dataset.source_name,
        source_as_of_date=dataset.source_as_of_date,
        imported_at=dataset.imported_at,
    )


def _risk_fields(prediction: RiskPrediction | None) -> RiskFields:
    if prediction is None:
        return RiskFields()
    return RiskFields(
        prediction_id=prediction.id,
        cost_risk_probability=prediction.cost_risk_probability,
        time_risk_probability=prediction.time_risk_probability,
        implementation_score=prediction.implementation_score,
        overall_score=prediction.overall_score,
        risk_band=prediction.risk_band,
        availability_status=prediction.availability_status,
        rule_version=prediction.rule_version,
        predicted_at=prediction.predicted_at,
    )


def _summary(
    snapshot: ProjectSnapshot, prediction: RiskPrediction | None
) -> ProjectSummary:
    return ProjectSummary(
        **_risk_fields(prediction).model_dump(),
        project_id=snapshot.project_id,
        project_code=snapshot.project.project_code,
        snapshot_id=snapshot.id,
        project_name=snapshot.project_name,
        sector=snapshot.sector,
        ministry=snapshot.ministry,
        implementing_agency=snapshot.implementing_agency,
        original_cost_cr=snapshot.original_cost_cr,
        revised_cost_cr=snapshot.revised_cost_cr,
        expenditure_cr=snapshot.expenditure_cr,
        physical_progress_pct=snapshot.physical_progress_pct,
        dataset=_freshness(snapshot.dataset),
    )


def _snapshot_query(
    *,
    dataset_id: int | None,
    sector: str | None,
    ministry: str | None,
    agency: str | None,
    min_cost: Decimal | None,
    max_cost: Decimal | None,
    min_progress: Decimal | None,
    max_progress: Decimal | None,
) -> Select:
    conditions = [Dataset.status == "completed"]
    if dataset_id is not None:
        conditions.append(ProjectSnapshot.dataset_id == dataset_id)
    if sector is not None:
        conditions.append(ProjectSnapshot.sector == sector)
    if ministry is not None:
        conditions.append(ProjectSnapshot.ministry == ministry)
    if agency is not None:
        conditions.append(ProjectSnapshot.implementing_agency == agency)
    if min_cost is not None:
        conditions.append(ProjectSnapshot.original_cost_cr >= min_cost)
    if max_cost is not None:
        conditions.append(ProjectSnapshot.original_cost_cr <= max_cost)
    if min_progress is not None:
        conditions.append(ProjectSnapshot.physical_progress_pct >= min_progress)
    if max_progress is not None:
        conditions.append(ProjectSnapshot.physical_progress_pct <= max_progress)
    return (
        select(ProjectSnapshot)
        .options(
            joinedload(ProjectSnapshot.project),
            joinedload(ProjectSnapshot.dataset),
        )
        .join(ProjectSnapshot.dataset)
        .where(*conditions)
        .order_by(ProjectSnapshot.id.asc())
    )


def _filtered_snapshots(
    session: Session,
    *,
    dataset_id: int | None,
    sector: str | None,
    ministry: str | None,
    agency: str | None,
    min_cost: Decimal | None,
    max_cost: Decimal | None,
    min_progress: Decimal | None,
    max_progress: Decimal | None,
) -> list[ProjectSnapshot]:
    return session.scalars(
        _snapshot_query(
            dataset_id=dataset_id,
            sector=sector,
            ministry=ministry,
            agency=agency,
            min_cost=min_cost,
            max_cost=max_cost,
            min_progress=min_progress,
            max_progress=max_progress,
        )
    ).all()


def _validate_bounds(
    minimum: Decimal | None, maximum: Decimal | None, name: str
) -> None:
    if minimum is not None and maximum is not None and minimum > maximum:
        raise HTTPException(
            status_code=422, detail=f"{name}_min cannot exceed {name}_max."
        )


def _matches_risk_band(
    session: Session, snapshot: ProjectSnapshot, risk_band: str | None
) -> bool:
    return risk_band is None or (
        (prediction := _latest_prediction(session, snapshot.id)) is not None
        and prediction.risk_band == risk_band
    )


@router.get("/projects", response_model=ProjectListResponse)
def list_projects(
    dataset_id: int | None = None,
    sector: str | None = None,
    ministry: str | None = None,
    agency: str | None = None,
    risk_band: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    min_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    max_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    min_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    max_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 100,
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    _validate_bounds(min_cost, max_cost, "cost")
    _validate_bounds(min_progress, max_progress, "progress")
    snapshots = _filtered_snapshots(
        db,
        dataset_id=dataset_id,
        sector=sector,
        ministry=ministry,
        agency=agency,
        min_cost=min_cost,
        max_cost=max_cost,
        min_progress=min_progress,
        max_progress=max_progress,
    )
    snapshot_ids = [s.id for s in snapshots]
    preds_map = get_latest_predictions_map(db, snapshot_ids)
    items = [
        (_summary(snapshot, preds_map.get(snapshot.id)))
        for snapshot in snapshots
    ]
    if risk_band is not None:
        items = [item for item in items if item.risk_band == risk_band]
    items.sort(
        key=lambda item: (
            item.overall_score is None,
            item.overall_score or Decimal("0"),
            item.project_id,
        )
    )
    dataset = items[0].dataset if items else None
    return ProjectListResponse(
        items=items[offset : offset + limit],
        page=Page(offset=offset, limit=limit, total=len(items)),
        dataset=dataset,
    )


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)) -> ProjectDetail:
    snapshot = db.scalar(
        select(ProjectSnapshot)
        .join(ProjectSnapshot.project)
        .join(ProjectSnapshot.dataset)
        .where(Project.id == project_id, Dataset.status == "completed")
        .order_by(ProjectSnapshot.id.desc())
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    features = derive_analytical_features(
        snapshot, source_as_of_date=snapshot.dataset.source_as_of_date
    )
    return ProjectDetail(
        **_summary(snapshot, _latest_prediction(db, snapshot.id)).model_dump(),
        original_commissioning_date=snapshot.original_commissioning_date,
        revised_commissioning_date=snapshot.revised_commissioning_date,
        sanction_date=snapshot.sanction_date,
        cost_increase_cr=features.cost_increase_cr,
        cost_escalation_pct=features.cost_escalation_pct,
        expenditure_to_original_cost_ratio=features.expenditure_to_original_cost_ratio,
        expenditure_to_revised_cost_ratio=features.expenditure_to_revised_cost_ratio,
        schedule_revision_days=features.schedule_revision_days,
        project_age_days=features.project_age_days,
        planned_duration_days=features.planned_duration_days,
        analysis_date_source=features.analysis_date_source,
        unavailable_reasons=features.unavailable_reasons,
    )


def _analytics(
    session: Session,
    snapshots: list[ProjectSnapshot],
    attribute: str,
) -> list[GroupAnalytics]:
    snapshot_ids = [s.id for s in snapshots]
    preds_map = get_latest_predictions_map(session, snapshot_ids)
    grouped: dict[str, list[tuple[ProjectSnapshot, RiskPrediction | None]]] = {}
    for snapshot in snapshots:
        val = getattr(snapshot, attribute, None) or "Unknown"
        grouped.setdefault(val, []).append((snapshot, preds_map.get(snapshot.id)))
    result = []
    for group, items in sorted(grouped.items()):
        scores = [
            pred.overall_score
            for _, pred in items
            if pred and pred.overall_score is not None
        ]
        result.append(
            GroupAnalytics(
                group=group,
                project_count=len(items),
                available_prediction_count=len(scores),
                average_overall_score=None if not scores else sum(scores) / len(scores),
                high_risk_projects=sum(pred is not None and pred.risk_band == "high" for _, pred in items),
                critical_projects=sum(pred is not None and pred.risk_band == "critical" for _, pred in items),
            )
        )
    return result


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    dataset_id: int | None = None,
    sector: str | None = None,
    ministry: str | None = None,
    agency: str | None = None,
    risk_band: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    min_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    max_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    min_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    max_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    db: Session = Depends(get_db),
) -> DashboardSummary:
    cache_key = f"dash_summary:{dataset_id}:{sector}:{ministry}:{agency}:{risk_band}:{min_cost}:{max_cost}:{min_progress}:{max_progress}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    _validate_bounds(min_cost, max_cost, "cost")
    _validate_bounds(min_progress, max_progress, "progress")
    snapshots = _filtered_snapshots(
        db,
        dataset_id=dataset_id,
        sector=sector,
        ministry=ministry,
        agency=agency,
        min_cost=min_cost,
        max_cost=max_cost,
        min_progress=min_progress,
        max_progress=max_progress,
    )
    snapshot_ids = [s.id for s in snapshots]
    preds_map = get_latest_predictions_map(db, snapshot_ids)
    if risk_band is not None:
        snapshots = [
            s for s in snapshots
            if (p := preds_map.get(s.id)) is not None and p.risk_band == risk_band
        ]
    scores = [
        p.overall_score for s in snapshots
        if (p := preds_map.get(s.id)) is not None and p.overall_score is not None
    ]
    high_count = sum(
        1 for s in snapshots
        if (p := preds_map.get(s.id)) is not None and p.risk_band == "high"
    )
    crit_count = sum(
        1 for s in snapshots
        if (p := preds_map.get(s.id)) is not None and p.risk_band == "critical"
    )
    total_revised = sum(
        (s.revised_cost_cr for s in snapshots if s.revised_cost_cr is not None),
        Decimal("0"),
    )
    res = DashboardSummary(
        total_projects=len(snapshots),
        available_predictions=len(scores),
        high_risk_projects=high_count,
        critical_projects=crit_count,
        average_overall_score=None if not scores else sum(scores) / len(scores),
        total_original_cost_cr=sum(
            (s.original_cost_cr for s in snapshots), Decimal("0")
        ),
        total_revised_cost_cr=total_revised,
        total_expenditure_cr=sum((s.expenditure_cr for s in snapshots), Decimal("0")),
        dataset=_freshness(snapshots[0].dataset) if snapshots else None,
    )
    set_cached(cache_key, res)
    return res


@router.get("/analytics/sectors", response_model=list[GroupAnalytics])
def sector_analytics(
    dataset_id: int | None = None,
    sector: str | None = None,
    ministry: str | None = None,
    agency: str | None = None,
    risk_band: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    min_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    max_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    min_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    max_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    db: Session = Depends(get_db),
) -> list[GroupAnalytics]:
    cache_key = f"sec_analytics:{dataset_id}:{sector}:{ministry}:{agency}:{risk_band}:{min_cost}:{max_cost}:{min_progress}:{max_progress}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    _validate_bounds(min_cost, max_cost, "cost")
    _validate_bounds(min_progress, max_progress, "progress")
    snapshots = _filtered_snapshots(
        db,
        dataset_id=dataset_id,
        sector=sector,
        ministry=ministry,
        agency=agency,
        min_cost=min_cost,
        max_cost=max_cost,
        min_progress=min_progress,
        max_progress=max_progress,
    )
    if risk_band is not None:
        preds_map = get_latest_predictions_map(db, [s.id for s in snapshots])
        snapshots = [
            s for s in snapshots
            if (p := preds_map.get(s.id)) is not None and p.risk_band == risk_band
        ]
    res = _analytics(db, snapshots, "sector")
    set_cached(cache_key, res)
    return res


@router.get("/analytics/ministries", response_model=list[GroupAnalytics])
def ministry_analytics(
    dataset_id: int | None = None,
    sector: str | None = None,
    ministry: str | None = None,
    agency: str | None = None,
    risk_band: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    min_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    max_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    min_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    max_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    db: Session = Depends(get_db),
) -> list[GroupAnalytics]:
    cache_key = f"min_analytics:{dataset_id}:{sector}:{ministry}:{agency}:{risk_band}:{min_cost}:{max_cost}:{min_progress}:{max_progress}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    _validate_bounds(min_cost, max_cost, "cost")
    _validate_bounds(min_progress, max_progress, "progress")
    snapshots = _filtered_snapshots(
        db,
        dataset_id=dataset_id,
        sector=sector,
        ministry=ministry,
        agency=agency,
        min_cost=min_cost,
        max_cost=max_cost,
        min_progress=min_progress,
        max_progress=max_progress,
    )
    if risk_band is not None:
        preds_map = get_latest_predictions_map(db, [s.id for s in snapshots])
        snapshots = [
            s for s in snapshots
            if (p := preds_map.get(s.id)) is not None and p.risk_band == risk_band
        ]
    res = _analytics(db, snapshots, "ministry")
    set_cached(cache_key, res)
    return res


@router.get("/analytics/benchmarks", response_model=BenchmarkResponse)
def project_benchmark(
    project_id: int,
    minimum_peers: Annotated[int, Query(ge=1, le=100)] = 10,
    db: Session = Depends(get_db),
) -> BenchmarkResponse:
    detail = get_project(project_id, db)
    subject = db.scalar(
        select(ProjectSnapshot).where(ProjectSnapshot.id == detail.snapshot_id)
    )
    if subject is None:
        raise HTTPException(status_code=404, detail="Project snapshot not found.")
    all_snapshots = _filtered_snapshots(
        db,
        dataset_id=subject.dataset_id,
        sector=None,
        ministry=None,
        agency=None,
        min_cost=None,
        max_cost=None,
        min_progress=None,
        max_progress=None,
    )
    peers = [
        (item, prediction)
        for item in all_snapshots
        if (prediction := _latest_prediction(db, item.id)) is not None
    ]
    result = benchmark(
        subject,
        peers,
        subject_prediction=_latest_prediction(db, subject.id),
        minimum_peers=minimum_peers,
    )
    return BenchmarkResponse(project_id=project_id, **result.__dict__)


@router.get("/risk/projects", response_model=ProjectListResponse)
def risk_projects(
    dataset_id: int | None = None,
    sector: str | None = None,
    ministry: str | None = None,
    agency: str | None = None,
    risk_band: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    min_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    max_cost: Annotated[Decimal | None, Query(ge=0)] = None,
    min_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    max_progress: Annotated[Decimal | None, Query(ge=0, le=100)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 100,
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    return list_projects(
        dataset_id,
        sector,
        ministry,
        agency,
        risk_band,
        min_cost,
        max_cost,
        min_progress,
        max_progress,
        offset,
        limit,
        db,
    )


@router.get("/risk/projects/{project_id}", response_model=ProjectDetail)
def risk_project(project_id: int, db: Session = Depends(get_db)) -> ProjectDetail:
    return get_project(project_id, db)


@router.get(
    "/risk/projects/{project_id}/explanation", response_model=RiskExplanationResponse
)
def risk_explanation(
    project_id: int, db: Session = Depends(get_db)
) -> RiskExplanationResponse:
    detail = get_project(project_id, db)
    if detail.prediction_id is None:
        raise HTTPException(status_code=404, detail="Risk prediction not found.")
    prediction = db.get(RiskPrediction, detail.prediction_id)
    explanations = db.scalars(
        select(RiskExplanation)
        .where(RiskExplanation.prediction_id == detail.prediction_id)
        .order_by(RiskExplanation.shap_contribution.desc())
    ).all()
    return RiskExplanationResponse(
        prediction_id=prediction.id,
        project_id=project_id,
        rule_version=prediction.rule_version,
        overall_score=prediction.overall_score,
        risk_band=prediction.risk_band,
        explanations=[
            RiskExplanationItem.model_validate(item) for item in explanations
        ],
    )


@router.get("/alerts", response_model=AlertListResponse)
def list_alerts(
    status: str | None = Query(default=None, pattern="^(open|acknowledged|closed)$"),
    severity: str | None = Query(
        default=None, pattern="^(normal|watch|high|critical)$"
    ),
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 100,
    db: Session = Depends(get_db),
) -> AlertListResponse:
    query = select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc())
    count_query = select(func.count()).select_from(Alert)
    conditions = []
    if status is not None:
        conditions.append(Alert.status == status)
    if severity is not None:
        conditions.append(Alert.severity == severity)
    alerts = db.scalars(query.where(*conditions).offset(offset).limit(limit)).all()
    total = db.scalar(count_query.where(*conditions)) or 0
    return AlertListResponse(
        items=[AlertResponse.model_validate(alert) for alert in alerts],
        page=Page(offset=offset, limit=limit, total=total),
    )


@router.get(
    "/monitoring/snapshot-comparison",
    response_model=SnapshotComparisonResponse,
    summary="Compare two monitoring snapshots",
    description="Compares the current completed dataset against a previous one, matched by stable "
    "project_id. Reports portfolio deltas, risk movements (new high/critical, improved, "
    "deteriorated), related warnings, and per-dataset score history. Returns an unavailable "
    "reason instead of deltas when only one completed snapshot exists.",
)
def snapshot_comparison(
    current_dataset_id: int | None = None,
    previous_dataset_id: int | None = None,
    sector: str | None = None,
    ministry: str | None = None,
    risk_band: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    db: Session = Depends(get_db),
) -> SnapshotComparisonResponse:
    return compare_snapshots(
        db,
        current_dataset_id=current_dataset_id,
        previous_dataset_id=previous_dataset_id,
        sector=sector,
        ministry=ministry,
        risk_band=risk_band,
    )
