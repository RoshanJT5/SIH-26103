from datetime import date, datetime, timezone
from decimal import Decimal

from backend.app.models import Dataset, Project, ProjectSnapshot, RiskPrediction
from backend.app.services.assistant import answer_question, parse_intent


def seed_assistant_data(session_factory):
    with session_factory() as session:
        dataset = Dataset(source_name="assistant.csv", checksum="b" * 64, status="completed", accepted_count=1, rejected_count=0)
        project = Project(project_code="ROAD-001")
        session.add_all([dataset, project])
        session.flush()
        snapshot = ProjectSnapshot(
            project_id=project.id, dataset_id=dataset.id, source_row_number=1, project_name="North Road",
            sector="Roads", ministry="Works", implementing_agency="Agency", original_cost_cr=Decimal("100"),
            revised_cost_cr=Decimal("125"), expenditure_cr=Decimal("60"), physical_progress_pct=Decimal("40"),
            original_commissioning_date=date(2025, 1, 1), revised_commissioning_date=date(2026, 1, 1),
            sanction_date=date(2024, 1, 1), raw_values={}, quality_flags=[],
        )
        session.add(snapshot)
        session.flush()
        session.add(RiskPrediction(
            snapshot_id=snapshot.id, cost_risk_probability=Decimal("0.70"), time_risk_probability=Decimal("0.80"),
            implementation_score=Decimal("50"), overall_score=Decimal("74"), rule_version="risk-rules-v1",
            risk_band="high", availability_status="available", predicted_at=datetime.now(timezone.utc),
        ))
        session.commit()


def test_intent_parser_validates_supported_question_shapes():
    assert parse_intent("show the highest risk projects").intent == "rank_projects"
    assert parse_intent('explain the risk for "North Road"').intent == "explain_project"
    assert parse_intent("summarize the Roads sector").intent == "summarize_group"
    assert parse_intent('compare "North Road" with peers').intent == "compare_peers"


def test_assistant_uses_bounded_retrieval_and_mocked_provider(migrated_database):
    _, _, session_factory = migrated_database
    seed_assistant_data(session_factory)
    with session_factory() as session:
        retrieval, answer, status, model = answer_question(
            session,
            'explain the risk for "North Road"',
            None,
            provider=lambda question, result: f"Grounded: {result.answer}",
        )
    assert status == "groq"
    assert model is not None
    assert "ROAD-001" in answer
    assert retrieval.sources[0]["source_type"] == "project"


def test_assistant_explicitly_resolves_unknown_projects(migrated_database, monkeypatch):
    _, _, session_factory = migrated_database
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GROQ_MODEL", "")
    from backend.app.core.config import get_settings

    get_settings.cache_clear()
    seed_assistant_data(session_factory)
    with session_factory() as session:
        retrieval, answer, status, _ = answer_question(session, 'explain the risk for "Missing Road"', None)
    assert status == "disabled"
    assert "could not find" in answer.lower()
    assert retrieval.sources == []