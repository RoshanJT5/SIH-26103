from collections.abc import Callable
from datetime import date
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Dataset

T = TypeVar("T")


def get_dataset_by_checksum(session: Session, checksum: str) -> Dataset | None:
    return session.scalar(select(Dataset).where(Dataset.checksum == checksum))


def create_dataset_idempotently(
    session: Session,
    *,
    source_name: str,
    checksum: str,
    source_as_of_date: date | None = None,
) -> tuple[Dataset, bool]:
    existing = get_dataset_by_checksum(session, checksum)
    if existing is not None:
        return existing, False
    dataset = Dataset(
        source_name=source_name,
        checksum=checksum,
        source_as_of_date=source_as_of_date,
        status="pending",
    )
    try:
        with session.begin_nested():
            session.add(dataset)
            session.flush()
    except IntegrityError:
        existing = get_dataset_by_checksum(session, checksum)
        if existing is None:
            raise
        return existing, False
    return dataset, True


def run_atomic_import(session: Session, importer: Callable[[Session, Dataset], T], dataset: Dataset) -> T:
    try:
        result = importer(session, dataset)
        dataset.status = "completed"
        session.commit()
        return result
    except Exception:
        session.rollback()
        raise

