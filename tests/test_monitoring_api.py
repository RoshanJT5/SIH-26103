from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Dataset, Project, ProjectSnapshot, RiskPrediction


def seed_monitoring_data(session_factory):
    with session_factory() as session:
        dataset = Dataset(
            source_name="test.csv",
            checksum="a" * 64,
            source_as_of_date=date(2026, 9, 1),
            status="completed",
            accepted_count=2,
            rejected_count=0,
        )
        first_project = Project(project_code="P-001")
        second_project = Project(project_code="P-002")
        session.add_all([dataset, first_project, second_project])
        session.flush()
        first_snapshot = ProjectSnapshot(
            project_id=first_project.id,
            dataset_id=dataset.id,
            source_row_number=1,
            project_name="Road One",
            sector="Roads",
            ministry="Works",
            implementing_agency="Agency A",
            original_cost_cr=Decimal("100"),
            revised_cost_cr=Decimal("120"),
            expenditure_cr=Decimal("60"),
            physical_progress_pct=Decimal("40"),
            original_commissioning_date=date(2025, 1, 1),
            revised_commissioning_date=date(2026, 1, 1),
            sanction_date=date(2024, 1, 1),
            raw_values={},
            quality_flags=[],
        )
        second_snapshot = ProjectSnapshot(
            project_id=second_project.id,
            dataset_id=dataset.id,
            source_row_number=2,
            project_name="Water Two",
            sector="Water",
            ministry="Works",
            implementing_agency="Agency B",
            original_cost_cr=Decimal("200"),
            revised_cost_cr=None,
            expenditure_cr=Decimal("20"),
            physical_progress_pct=Decimal("80"),
            original_commissioning_date=date(2025, 1, 1),
            revised_commissioning_date=None,
            sanction_date=date(2024, 1, 1),
            raw_values={},
            quality_flags=[],
        )
        session.add_all([first_snapshot, second_snapshot])
        session.flush()
        session.add(
            RiskPrediction(
                snapshot_id=first_snapshot.id,
                cost_risk_probability=Decimal("0.70"),
                time_risk_probability=Decimal("0.80"),
                implementation_score=Decimal("50"),
                overall_score=Decimal("74"),
                rule_version="risk-rules-v1",
                risk_band="high",
                availability_status="available",
                predicted_at=datetime.now(timezone.utc),
            )
        )
        session.commit()


def test_monitoring_endpoints_share_filters_and_handle_missing_predictions(migrated_database):
    _, _, session_factory = migrated_database
    seed_monitoring_data(session_factory)

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            projects = client.get("/api/projects?sector=Roads&limit=1")
            assert projects.status_code == 200
            assert projects.json()["page"] == {"offset": 0, "limit": 1, "total": 1}
            assert projects.json()["items"][0]["risk_band"] == "high"

            summary = client.get("/api/dashboard/summary")
            assert summary.status_code == 200
            assert summary.json()["total_projects"] == 2
            assert summary.json()["available_predictions"] == 1

            risk_projects = client.get("/api/risk/projects?risk_band=high")
            assert risk_projects.status_code == 200
            assert len(risk_projects.json()["items"]) == 1

            detail = client.get("/api/risk/projects/1")
            assert detail.status_code == 200
            assert detail.json()["cost_escalation_pct"] == "20.00"

            missing = client.get("/api/projects/999")
            assert missing.status_code == 404
    finally:
        app.dependency_overrides.clear()