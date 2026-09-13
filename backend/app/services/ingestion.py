from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import AuditEvent, Dataset, IngestionIssue, Project, ProjectSnapshot
from .csv_upload import ValidatedCsv


@dataclass(frozen=True)
class PersistedImport:
    dataset: Dataset
    created: bool
    issue_count: int


def _load_projects(session: Session, codes: list[str]) -> dict[str, Project]:
    projects: dict[str, Project] = {}
    for start in range(0, len(codes), 500):
        batch = codes[start : start + 500]
        for project in session.scalars(select(Project).where(Project.project_code.in_(batch))):
            projects[project.project_code] = project
    return projects


def persist_validated_import(
    session: Session,
    *,
    parsed: ValidatedCsv,
    source_name: str,
    checksum: str,
    source_as_of_date: date | None,
) -> PersistedImport:
    existing = session.scalar(select(Dataset).where(Dataset.checksum == checksum))
    if existing is not None:
        issue_count = session.scalar(
            select(func.count()).select_from(IngestionIssue).where(IngestionIssue.dataset_id == existing.id)
        ) or 0
        return PersistedImport(existing, False, issue_count)

    dataset = Dataset(
        source_name=source_name,
        checksum=checksum,
        source_as_of_date=source_as_of_date,
        status="pending",
        accepted_count=len(parsed.projects),
        rejected_count=parsed.rejected_count,
    )

    try:
        session.add(dataset)
        session.flush()

        codes = [record.project_code for record in parsed.projects]
        projects_by_code = _load_projects(session, codes)
        for code in codes:
            if code not in projects_by_code:
                project = Project(project_code=code)
                session.add(project)
                projects_by_code[code] = project
        session.flush()

        for record in parsed.projects:
            session.add(
                ProjectSnapshot(
                    project_id=projects_by_code[record.project_code].id,
                    dataset_id=dataset.id,
                    source_row_number=record.source_row_number,
                    project_name=record.project_name,
                    sector=record.sector,
                    ministry=record.ministry,
                    implementing_agency=record.implementing_agency,
                    original_cost_cr=record.original_cost_cr,
                    revised_cost_cr=record.revised_cost_cr,
                    expenditure_cr=record.expenditure_cr,
                    physical_progress_pct=record.physical_progress_pct,
                    original_commissioning_date=record.original_commissioning_date,
                    revised_commissioning_date=record.revised_commissioning_date,
                    sanction_date=record.sanction_date,
                    raw_values=record.raw_values,
                    quality_flags=record.quality_flags,
                )
            )

        session.add_all(
            [
                IngestionIssue(
                    dataset_id=dataset.id,
                    source_row_number=issue.source_row_number,
                    field=issue.field,
                    raw_value=issue.raw_value,
                    issue_code=issue.issue_code,
                    severity=issue.severity,
                    message=issue.message,
                )
                for issue in parsed.issues
            ]
        )
        dataset.status = "completed"
        session.add(AuditEvent(operation="dataset_import", dataset_id=dataset.id, outcome="success", details={"source_name": source_name, "accepted_count": dataset.accepted_count, "rejected_count": dataset.rejected_count, "issue_count": len(parsed.issues)}))
        session.commit()
        return PersistedImport(dataset, True, len(parsed.issues))
    except IntegrityError:
        session.rollback()
        raced_dataset = session.scalar(select(Dataset).where(Dataset.checksum == checksum))
        if raced_dataset is None:
            raise
        issue_count = session.scalar(
            select(func.count()).select_from(IngestionIssue).where(IngestionIssue.dataset_id == raced_dataset.id)
        ) or 0
        return PersistedImport(raced_dataset, False, issue_count)
    except Exception:
        session.rollback()
        raise

