from pathlib import Path
import csv
import io

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.services.csv_upload import inspect_project_csv

PROJECT_ROOT = Path(__file__).parents[1]
EXPECTED_COLUMNS = [
    "source_row_number",
    "sector",
    "ministry",
    "implementing_agency",
    "project_code",
    "project_name",
    "original_cost_cr",
    "revised_cost_cr",
    "expenditure_cr",
    "physical_progress_pct",
    "original_commissioning_date",
    "revised_commissioning_date",
    "sanction_date",
]
SOURCE_COLUMNS = [
    "Sr. No.", "Sector Name", "Line Ministry", "Implementing Agency", "Project Code",
    "Project Name", "Original Cost\n(in cr.)", "Revised Cost\n(in cr.)",
    "Expenditure\n(in cr.)", "Physical Progress\n(in %)",
    "Original\nDate of Commissioning", "Revised\nDate of Commissioning", "Sanction Date",
]


def make_report(rows: list[list[str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["Projects Details"])
    writer.writerow([])
    writer.writerow(SOURCE_COLUMNS)
    writer.writerows(rows)
    return stream.getvalue().encode()


@pytest.fixture
def api_client(migrated_database, monkeypatch):
    _, _, session_factory = migrated_database
    monkeypatch.setenv("ADMIN_USERNAME", "test-admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
    get_settings.cache_clear()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/auth/login",
                json={"username": "test-admin", "password": "test-password"},
            )
            assert login.status_code == 200
            client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
            yield client
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_supplied_report_preamble_and_multiline_headers_are_mapped():
    result = inspect_project_csv((PROJECT_ROOT / "DATA" / "Projects_Report.csv").read_bytes())

    assert result.preamble_rows == 2
    assert result.record_count == 1775
    assert result.canonical_columns == EXPECTED_COLUMNS


def test_upload_endpoint_validates_and_persists_supplied_report(api_client):
    report = PROJECT_ROOT / "DATA" / "Projects_Report.csv"
    with report.open("rb") as stream:
        response = api_client.post(
            "/api/projects/upload",
            data={"source_as_of_date": "2026-09-01"},
            files={"file": (report.name, stream, "text/csv")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["idempotent"] is False
    assert body["record_count"] == 1775
    assert body["accepted_count"] == 1775
    assert body["rejected_count"] == 0
    assert body["issue_count"] == 1546
    assert body["source_as_of_date"] == "2026-09-01"
    assert body["canonical_columns"] == EXPECTED_COLUMNS

    quality_response = api_client.get(f"/api/datasets/{body['dataset_id']}/quality?limit=25")
    assert quality_response.status_code == 200
    quality = quality_response.json()
    summary = {item["issue_code"]: item["count"] for item in quality["summary"]}
    assert quality["accepted_count"] == 1775
    assert quality["rejected_count"] == 0
    assert quality["issue_count"] == 1546
    assert len(quality["issues"]) == 25
    assert summary["zero_revised_cost"] == 833
    assert summary["missing_revised_commissioning_date"] == 348
    assert summary["missing_sanction_date"] == 12
    assert summary["zero_expenditure"] == 135
    assert summary["zero_physical_progress"] == 92

    with report.open("rb") as stream:
        repeated_response = api_client.post(
            "/api/projects/upload",
            files={"file": (report.name, stream, "text/csv")},
        )
    repeated = repeated_response.json()
    assert repeated_response.status_code == 200
    assert repeated["dataset_id"] == body["dataset_id"]
    assert repeated["idempotent"] is True


def test_upload_rejects_wrong_extension_and_content_type(api_client):
    wrong_extension = api_client.post(
        "/api/projects/upload",
        files={"file": ("report.txt", b"content", "text/plain")},
    )
    wrong_content_type = api_client.post(
        "/api/projects/upload",
        files={"file": ("report.csv", b"content", "application/pdf")},
    )

    assert wrong_extension.status_code == 415
    assert wrong_content_type.status_code == 415


def test_upload_rejects_oversized_file(api_client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "10")
    get_settings.cache_clear()
    try:
        response = api_client.post(
            "/api/projects/upload",
            files={"file": ("report.csv", b"x" * 11, "text/csv")},
        )
        assert response.status_code == 413
    finally:
        get_settings.cache_clear()


def test_upload_rejects_missing_or_malformed_schema(api_client):
    missing_headers = b'"Sr. No.","Project Code"\r\n"1","P-1"\r\n'
    malformed_record = (
        b'"Sr. No.","Sector Name","Line Ministry","Implementing Agency","Project Code",'
        b'"Project Name","Original Cost (in cr.)","Revised Cost (in cr.)",'
        b'"Expenditure (in cr.)","Physical Progress (in %)",'
        b'"Original Date of Commissioning","Revised Date of Commissioning","Sanction Date"\r\n'
        b'"1","Roads"\r\n'
    )

    missing_response = api_client.post(
        "/api/projects/upload",
        files={"file": ("report.csv", missing_headers, "text/csv")},
    )
    malformed_response = api_client.post(
        "/api/projects/upload",
        files={"file": ("report.csv", malformed_record, "text/csv")},
    )

    assert missing_response.status_code == 422
    assert "missing headers" in missing_response.json()["detail"]
    assert malformed_response.status_code == 422
    assert "expected 13 fields" in malformed_response.json()["detail"]


def test_quoted_newline_in_a_data_field_is_one_record():
    content = (
        '"Projects Details"\r\n\r\n'
        '"Sr. No.","Sector Name","Line Ministry","Implementing Agency","Project Code",'
        '"Project Name","Original Cost\n(in cr.)","Revised Cost\n(in cr.)",'
        '"Expenditure\n(in cr.)","Physical Progress\n(in %)",'
        '"Original\nDate of Commissioning","Revised\nDate of Commissioning","Sanction Date"\r\n'
        '"1","Roads","Ministry","Agency","P-1","Road\nProject","100","120","50",'
        '"25","01/01/2025","01/01/2026","01/01/2024"\r\n'
    ).encode()

    assert inspect_project_csv(content).record_count == 1


def test_invalid_and_conflicting_duplicate_rows_are_rejected_and_visible(api_client):
    content = make_report(
        [
            ["1", "Roads", "Ministry", "Agency", "P-1", "First", "100", "120", "50", "25", "01/01/2025", "01/01/2026", "01/01/2024"],
            ["2", "Roads", "Ministry", "Agency", "P-1", "Conflicting", "100", "120", "50", "25", "01/01/2025", "01/01/2026", "01/01/2024"],
            ["3", "Roads", "Ministry", "Agency", "P-2", "Invalid progress", "100", "120", "50", "101", "01/01/2025", "01/01/2026", "01/01/2024"],
        ]
    )

    upload = api_client.post(
        "/api/projects/upload",
        files={"file": ("quality.csv", content, "text/csv")},
    )
    assert upload.status_code == 200
    body = upload.json()
    assert body["accepted_count"] == 1
    assert body["rejected_count"] == 2

    quality = api_client.get(f"/api/datasets/{body['dataset_id']}/quality").json()
    codes = {item["issue_code"] for item in quality["issues"]}
    assert "conflicting_duplicate_project_code" in codes
    assert "invalid_field_value" in codes
