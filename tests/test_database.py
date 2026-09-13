from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from backend.app.models import Dataset, Project, ProjectSnapshot
from backend.app.services.database_backup import backup_database, restore_database
from backend.app.services.datasets import create_dataset_idempotently, run_atomic_import


def test_migration_creates_all_tables_and_pragmas(migrated_database):
    _, engine, _ = migrated_database
    expected = {
        "datasets", "projects", "project_snapshots", "ingestion_issues",
        "model_versions", "risk_predictions", "risk_explanations", "alerts", "audit_events",
    }
    with engine.connect() as connection:
        tables = {row[0] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        assert expected <= tables
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000
        assert connection.execute(text("PRAGMA journal_mode")).scalar_one().lower() == "wal"


def test_dataset_registration_is_idempotent(migrated_database):
    _, _, session_factory = migrated_database
    with session_factory() as session:
        first, created = create_dataset_idempotently(session, source_name="one.csv", checksum="a" * 64)
        session.commit()
        first_id = first.id
    with session_factory() as session:
        repeated, created_again = create_dataset_idempotently(session, source_name="renamed.csv", checksum="a" * 64)
        assert created is True
        assert created_again is False
        assert repeated.id == first_id


def test_atomic_import_rolls_back_records(migrated_database):
    _, _, session_factory = migrated_database
    with session_factory() as session:
        dataset, _ = create_dataset_idempotently(session, source_name="one.csv", checksum="b" * 64)
        session.commit()
        dataset_id = dataset.id

        def failing_import(active_session, _dataset):
            active_session.add(Project(project_code="P-FAIL"))
            active_session.flush()
            raise RuntimeError("invalid input")

        with pytest.raises(RuntimeError):
            run_atomic_import(session, failing_import, dataset)
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Project)) == 0
        assert session.get(Dataset, dataset_id).status == "pending"


def test_constraints_and_foreign_keys_are_enforced(migrated_database):
    _, _, session_factory = migrated_database
    with session_factory() as session:
        bad_snapshot = ProjectSnapshot(
            project_id=999,
            dataset_id=999,
            source_row_number=1,
            project_name="Invalid",
            sector="Roads",
            ministry="Ministry",
            implementing_agency="Agency",
            original_cost_cr=Decimal("100.00"),
            revised_cost_cr=None,
            expenditure_cr=Decimal("10.00"),
            physical_progress_pct=Decimal("25.00"),
            original_commissioning_date=date(2026, 1, 1),
            raw_values={},
            quality_flags=[],
        )
        session.add(bad_snapshot)
        with pytest.raises(IntegrityError):
            session.commit()


def test_backup_restore_and_restart_persistence(migrated_database):
    database_path, engine, session_factory = migrated_database
    with session_factory() as session:
        session.add(Dataset(source_name="one.csv", checksum="c" * 64, status="completed"))
        session.commit()
    engine.dispose()

    backup_path = database_path.parent / "backup.db"
    restored_path = database_path.parent / "restored.db"
    backup_database(database_path, backup_path)
    restore_database(backup_path, restored_path)

    from backend.app.db.session import create_sqlite_engine

    restarted_engine = create_sqlite_engine(f"sqlite:///{restored_path.as_posix()}")
    restarted_session = sessionmaker(bind=restarted_engine)
    try:
        with restarted_session() as session:
            assert session.scalar(select(func.count()).select_from(Dataset)) == 1
    finally:
        restarted_engine.dispose()
