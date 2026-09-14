"""Snapshot comparison service.

Compares two completed project-monitoring snapshots and reports what changed
since the previous monitoring cycle. Projects are matched by stable
``Project.id`` — never by CSV row position.

Methodology version: ``snapshot-comparison-v1``.
"""

from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Alert, Dataset, ProjectSnapshot, RiskPrediction
from ..schemas.monitoring import (
    AlertResponse,
    DatasetRef,
    PortfolioDelta,
    ProjectMovement,
    ScoreHistoryPoint,
    SnapshotComparisonResponse,
)

VERSION = "snapshot-comparison-v1"
BAND_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
HIGH_BANDS = {"high", "critical"}
WARNING_LIMIT = 200


@dataclass
class _Row:
    project_id: int
    project_code: str
    project_name: str
    sector: str
    ministry: str
    revised_cost_cr: Decimal | None
    expenditure_cr: Decimal
    overall_score: Decimal | None
    risk_band: str | None


def _latest_prediction(session: Session, snapshot_id: int) -> RiskPrediction | None:
    return session.scalar(
        select(RiskPrediction)
        .where(RiskPrediction.snapshot_id == snapshot_id)
        .order_by(RiskPrediction.predicted_at.desc(), RiskPrediction.id.desc())
        .limit(1)
    )


def _dataset_rows(
    session: Session,
    dataset_id: int,
    sector: str | None,
    ministry: str | None,
) -> list[_Row]:
    conditions = [ProjectSnapshot.dataset_id == dataset_id]
    if sector is not None:
        conditions.append(ProjectSnapshot.sector == sector)
    if ministry is not None:
        conditions.append(ProjectSnapshot.ministry == ministry)
    snapshots = session.scalars(
        select(ProjectSnapshot).where(*conditions).order_by(ProjectSnapshot.id.asc())
    ).all()
    rows: list[_Row] = []
    for snapshot in snapshots:
        prediction = _latest_prediction(session, snapshot.id)
        rows.append(
            _Row(
                project_id=snapshot.project_id,
                project_code=snapshot.project.project_code,
                project_name=snapshot.project_name,
                sector=snapshot.sector,
                ministry=snapshot.ministry,
                revised_cost_cr=snapshot.revised_cost_cr,
                expenditure_cr=snapshot.expenditure_cr,
                overall_score=prediction.overall_score if prediction else None,
                risk_band=prediction.risk_band if prediction else None,
            )
        )
    return rows


def _aggregate(rows: list[_Row]) -> dict:
    scores = [row.overall_score for row in rows if row.overall_score is not None]
    revised = [row.revised_cost_cr for row in rows if row.revised_cost_cr is not None]
    return {
        "count": len(rows),
        "high": sum(row.risk_band == "high" for row in rows),
        "critical": sum(row.risk_band == "critical" for row in rows),
        "average": None if not scores else sum(scores) / len(scores),
        "revised": sum(revised, Decimal("0")),
        "expenditure": sum((row.expenditure_cr for row in rows), Decimal("0")),
    }


def _completed_dataset(session: Session, dataset_id: int) -> Dataset:
    dataset = session.scalar(
        select(Dataset).where(Dataset.id == dataset_id, Dataset.status == "completed")
    )
    if dataset is None:
        raise HTTPException(status_code=404, detail="Completed dataset not found.")
    return dataset


def _ref(dataset: Dataset) -> DatasetRef:
    return DatasetRef(
        dataset_id=dataset.id,
        source_name=dataset.source_name,
        source_as_of_date=dataset.source_as_of_date,
        imported_at=dataset.imported_at,
        status=dataset.status,
    )


def _movement(previous: _Row | None, current: _Row) -> ProjectMovement:
    change = None
    if (
        previous is not None
        and previous.overall_score is not None
        and current.overall_score is not None
    ):
        change = current.overall_score - previous.overall_score
    return ProjectMovement(
        project_id=current.project_id,
        project_code=current.project_code,
        project_name=current.project_name,
        sector=current.sector,
        ministry=current.ministry,
        previous_score=previous.overall_score if previous else None,
        current_score=current.overall_score,
        score_change=change,
        previous_band=previous.risk_band if previous else None,
        current_band=current.risk_band,
    )


def compare_snapshots(
    session: Session,
    *,
    current_dataset_id: int | None,
    previous_dataset_id: int | None,
    sector: str | None,
    ministry: str | None,
    risk_band: str | None,
) -> SnapshotComparisonResponse:
    completed_ids = session.scalars(
        select(Dataset.id)
        .where(Dataset.status == "completed")
        .order_by(Dataset.id.desc())
    ).all()
    if not completed_ids:
        raise HTTPException(status_code=404, detail="No completed datasets available.")

    current = (
        _completed_dataset(session, current_dataset_id)
        if current_dataset_id is not None
        else _completed_dataset(session, completed_ids[0])
    )
    if previous_dataset_id is not None:
        if previous_dataset_id >= current.id:
            raise HTTPException(
                status_code=422,
                detail="previous_dataset_id must reference an earlier dataset than current_dataset_id.",
            )
        previous = _completed_dataset(session, previous_dataset_id)
    else:
        older = [dataset_id for dataset_id in completed_ids if dataset_id < current.id]
        previous = _completed_dataset(session, older[0]) if older else None

    current_rows = _dataset_rows(session, current.id, sector, ministry)
    previous_rows = (
        _dataset_rows(session, previous.id, sector, ministry) if previous else []
    )
    current_stats = _aggregate(current_rows)
    previous_stats = _aggregate(previous_rows) if previous else None

    def band_ok(row: _Row) -> bool:
        return risk_band is None or row.risk_band == risk_band

    previous_by_project = {row.project_id: row for row in previous_rows}
    new_high, new_critical, improved, deteriorated = [], [], [], []
    for row in current_rows:
        if not band_ok(row):
            continue
        prev = previous_by_project.get(row.project_id)
        movement = _movement(prev, row)
        if row.risk_band in HIGH_BANDS and (
            prev is None or prev.risk_band not in HIGH_BANDS
        ):
            new_high.append(movement)
        if row.risk_band == "critical" and (
            prev is None or prev.risk_band != "critical"
        ):
            new_critical.append(movement)
        if (
            prev is not None
            and row.risk_band in BAND_ORDER
            and prev.risk_band in BAND_ORDER
        ):
            if BAND_ORDER[row.risk_band] > BAND_ORDER[prev.risk_band]:
                deteriorated.append(movement)
            elif BAND_ORDER[row.risk_band] < BAND_ORDER[prev.risk_band]:
                improved.append(movement)

    new_high.sort(key=lambda m: (m.current_score is None, -(m.current_score or 0)))
    new_critical.sort(key=lambda m: (m.current_score is None, -(m.current_score or 0)))
    deteriorated.sort(key=lambda m: (m.score_change is None, -(m.score_change or 0)))
    improved.sort(key=lambda m: (m.score_change is None, m.score_change or 0))

    attention_ids = {m.project_id for m in (*new_high, *deteriorated)}
    warnings: list[AlertResponse] = []
    if attention_ids:
        alerts = session.scalars(
            select(Alert)
            .join(ProjectSnapshot, ProjectSnapshot.id == Alert.snapshot_id)
            .where(
                ProjectSnapshot.dataset_id == current.id,
                ProjectSnapshot.project_id.in_(attention_ids),
            )
            .order_by(Alert.created_at.desc(), Alert.id.desc())
            .limit(WARNING_LIMIT)
        ).all()
        warnings = [AlertResponse.model_validate(alert) for alert in alerts]

    history: list[ScoreHistoryPoint] = []
    for dataset_id in sorted(completed_ids):
        dataset = _completed_dataset(session, dataset_id)
        stats = _aggregate(_dataset_rows(session, dataset_id, sector, ministry))
        history.append(
            ScoreHistoryPoint(
                dataset_id=dataset.id,
                source_name=dataset.source_name,
                source_as_of_date=dataset.source_as_of_date,
                project_count=stats["count"],
                average_overall_score=stats["average"],
                high_risk_projects=stats["high"],
                critical_projects=stats["critical"],
            )
        )

    if previous_stats is None:
        portfolio = PortfolioDelta(
            project_count=current_stats["count"],
            high_risk_projects=current_stats["high"],
            critical_projects=current_stats["critical"],
            average_overall_score=current_stats["average"],
            total_revised_cost_cr=current_stats["revised"],
            total_expenditure_cr=current_stats["expenditure"],
        )
        reason = "Only one completed dataset is available; comparison requires a previous snapshot."
    else:
        portfolio = PortfolioDelta(
            project_count=current_stats["count"],
            project_count_change=current_stats["count"] - previous_stats["count"],
            high_risk_projects=current_stats["high"],
            high_risk_change=current_stats["high"] - previous_stats["high"],
            critical_projects=current_stats["critical"],
            critical_change=current_stats["critical"] - previous_stats["critical"],
            average_overall_score=current_stats["average"],
            average_score_change=(current_stats["average"] - previous_stats["average"])
            if current_stats["average"] is not None
            and previous_stats["average"] is not None
            else None,
            total_revised_cost_cr=current_stats["revised"],
            revised_cost_change=current_stats["revised"] - previous_stats["revised"],
            total_expenditure_cr=current_stats["expenditure"],
            expenditure_change=current_stats["expenditure"]
            - previous_stats["expenditure"],
        )
        reason = None

    return SnapshotComparisonResponse(
        version=VERSION,
        current_dataset=_ref(current),
        previous_dataset=_ref(previous) if previous else None,
        portfolio=portfolio,
        new_high_risk_projects=new_high,
        new_critical_projects=new_critical,
        improved_projects=improved,
        deteriorated_projects=deteriorated,
        new_warnings=warnings,
        score_history=history,
        unavailable_reason=reason,
    )
