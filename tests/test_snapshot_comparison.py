from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Alert, Dataset, Project, ProjectSnapshot, RiskPrediction


def _snapshot(session, project, dataset, row, name, sector, cost):
    snapshot = ProjectSnapshot(
        project_id=project.id,
        dataset_id=dataset.id,
        source_row_number=row,
        project_name=name,
        sector=sector,
        ministry="Works",
        implementing_agency="Agency",
        original_cost_cr=Decimal("100"),
        revised_cost_cr=Decimal(str(cost)),
        expenditure_cr=Decimal("40"),
        physical_progress_pct=Decimal("50"),
        original_commissioning_date=date(2025, 1, 1),
        revised_commissioning_date=date(2026, 1, 1),
        sanction_date=date(2024, 1, 1),
        raw_values={},
        quality_flags=[],
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def _prediction(session, snapshot, score, band):
    prediction = RiskPrediction(
        snapshot_id=snapshot.id,
        cost_risk_probability=Decimal(str(score / 100)),
        time_risk_probability=Decimal(str(score / 100)),
        implementation_score=Decimal(str(score)),
        overall_score=Decimal(str(score)),
        rule_version="risk-rules-v1",
        risk_band=band,
        availability_status="available",
        predicted_at=datetime.now(timezone.utc),
    )
    session.add(prediction)
    session.flush()
    return prediction


def seed_comparison_data(session_factory):
    with session_factory() as session:
        previous = Dataset(
            source_name="aug.csv",
            checksum="c" * 64,
            source_as_of_date=date(2026, 8, 1),
            status="completed",
            accepted_count=2,
            rejected_count=0,
        )
        current = Dataset(
            source_name="sep.csv",
            checksum="d" * 64,
            source_as_of_date=date(2026, 9, 1),
            status="completed",
            accepted_count=2,
            rejected_count=0,
        )
        first = Project(project_code="C-001")
        second = Project(project_code="C-002")
        third = Project(project_code="C-003")
        session.add_all([previous, current, first, second, third])
        session.flush()
        prev_first = _snapshot(session, first, previous, 1, "Road One", "Roads", 110)
        _prediction(session, prev_first, 55, "medium")
        prev_third = _snapshot(session, third, previous, 2, "Old Three", "Water", 100)
        _prediction(session, prev_third, 20, "low")
        cur_first = _snapshot(session, first, current, 1, "Road One", "Roads", 130)
        first_prediction = _prediction(session, cur_first, 74, "high")
        cur_second = _snapshot(session, second, current, 2, "Rail Two", "Rail", 150)
        _prediction(session, cur_second, 88, "critical")
        session.add(
            Alert(
                snapshot_id=cur_first.id,
                prediction_id=first_prediction.id,
                rule_version="risk-rules-v1",
                severity="high",
                message="Escalated to high band.",
                status="open",
                deduplication_key="cmp-alert-1",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        return previous.id, current.id


def client_for(session_factory):
    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_snapshot_comparison_reports_movements(migrated_database):
    _, _, session_factory = migrated_database
    previous_id, current_id = seed_comparison_data(session_factory)
    with client_for(session_factory) as client:
        response = client.get("/api/monitoring/snapshot-comparison")
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == "snapshot-comparison-v1"
        assert body["current_dataset"]["dataset_id"] == current_id
        assert body["previous_dataset"]["dataset_id"] == previous_id
        assert body["portfolio"]["project_count_change"] == 0
        assert body["portfolio"]["high_risk_change"] == 1
        assert body["portfolio"]["critical_change"] == 1
        assert {p["project_code"] for p in body["new_high_risk_projects"]} == {
            "C-001",
            "C-002",
        }
        assert [p["project_code"] for p in body["new_critical_projects"]] == ["C-002"]
        deteriorated = {p["project_code"]: p for p in body["deteriorated_projects"]}
        assert set(deteriorated) == {"C-001"}
        assert float(deteriorated["C-001"]["score_change"]) == 19
        assert body["improved_projects"] == []
        assert len(body["new_warnings"]) == 1
        assert body["new_warnings"][0]["deduplication_key"] == "cmp-alert-1"
        assert len(body["score_history"]) == 2
        assert body["unavailable_reason"] is None


def test_snapshot_comparison_validates_and_filters(migrated_database):
    _, _, session_factory = migrated_database
    previous_id, current_id = seed_comparison_data(session_factory)
    with client_for(session_factory) as client:
        assert (
            client.get(
                "/api/monitoring/snapshot-comparison?current_dataset_id=9999"
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/api/monitoring/snapshot-comparison?current_dataset_id={previous_id}&previous_dataset_id={current_id}"
            ).status_code
            == 422
        )
        Rakhi = client.get(
            "/api/monitoring/snapshot-comparison?risk_band=critical"
        ).json()
        assert [p["project_code"] for p in Rakhi["new_high_risk_projects"]] == ["C-002"]
        sector = client.get("/api/monitoring/snapshot-comparison?sector=Water").json()
        assert sector["portfolio"]["project_count"] == 0
        assert sector["new_high_risk_projects"] == []


def test_snapshot_comparison_single_dataset_is_unavailable(migrated_database):
    _, _, session_factory = migrated_database
    with session_factory() as session:
        session.add(
            Dataset(
                source_name="only.csv",
                checksum="e" * 64,
                status="completed",
                accepted_count=0,
                rejected_count=0,
            )
        )
        session.commit()
    with client_for(session_factory) as client:
        body = client.get("/api/monitoring/snapshot-comparison").json()
        assert body["previous_dataset"] is None
        assert body["portfolio"]["project_count_change"] is None
        assert body["unavailable_reason"] is not None


def test_datasets_list_endpoint(migrated_database):
    _, _, session_factory = migrated_database
    seed_comparison_data(session_factory)
    with client_for(session_factory) as client:
        body = client.get("/api/datasets").json()
        assert [d["source_name"] for d in body] == ["sep.csv", "aug.csv"]
        assert body[0]["status"] == "completed"
