import time
import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import app


@pytest.fixture
def test_setup(migrated_database):
    _, _, session_factory = migrated_database

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        unique = int(time.time() * 1000)
        username = f"officer_{unique}"
        email = f"officer_{unique}@gov.in"
        resp = client.post(
            "/api/auth/signup",
            json={
                "name": "Nodal Officer",
                "email": email,
                "username": username,
                "password": "ValidPassword123!",
            },
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        yield client, auth_headers

    app.dependency_overrides.clear()


def test_create_project_lifecycle(test_setup):
    client, auth_headers = test_setup

    # 1. Create a single new project
    unique_code = f"TEST-PRJ-{int(time.time() * 1000)}"
    payload = {
        "project_code": unique_code,
        "project_name": "Dedicated High-Speed Freight Corridor Section 9",
        "sector": "Railways",
        "ministry": "Ministry of Railways",
        "implementing_agency": "RVNL",
        "original_cost_cr": 2500.0,
        "revised_cost_cr": 3100.0,
        "expenditure_cr": 800.0,
        "physical_progress_pct": 32.5,
        "original_commissioning_date": "2027-12-31",
        "revised_commissioning_date": "2028-06-30",
        "sanction_date": "2021-03-15",
    }

    resp = client.post("/api/projects", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["project_code"] == unique_code
    assert data["project_id"] > 0
    assert data["overall_score"] is not None
    assert data["risk_band"] in ["low", "medium", "high", "critical"]
    assert data["redirect_url"] == f"/projects/{data['project_id']}"

    # 2. Verify project details endpoint
    detail_resp = client.get(f"/api/projects/{data['project_id']}", headers=auth_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["project_code"] == unique_code
    assert detail["project_name"] == payload["project_name"]
    assert detail["cost_escalation_pct"] is not None
    assert detail["expenditure_to_original_cost_ratio"] is not None


def test_initialize_demo_endpoint(test_setup):
    client, auth_headers = test_setup
    resp = client.post("/api/projects/initialize-demo", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["initialized", "already_initialized", "ready"]
    assert data["dataset_id"] > 0


def test_early_warning_actions(test_setup):
    client, auth_headers = test_setup

    # Initialize demo to have warnings
    client.post("/api/projects/initialize-demo", headers=auth_headers)

    resp = client.get("/api/early-warnings?limit=1", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json().get("items", [])
    if not items:
        pytest.skip("No early warnings available to triage")

    w_id = items[0]["id"]

    # Acknowledge warning
    ack_resp = client.post(f"/api/early-warnings/{w_id}/acknowledge", headers=auth_headers)
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] in ["acknowledged", "closed"]

    # Close warning
    close_resp = client.post(f"/api/early-warnings/{w_id}/close", headers=auth_headers)
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"
