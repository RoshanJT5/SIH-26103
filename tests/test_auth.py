from fastapi.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.db.session import get_db
from backend.app.main import app


def test_admin_login_and_upload_protection(migrated_database, monkeypatch):
    _, _, session_factory = migrated_database
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    get_settings.cache_clear()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            unauthorized = client.post(
                "/api/projects/upload",
                files={"file": ("report.csv", b"invalid", "text/csv")},
            )
            assert unauthorized.status_code == 401

            invalid = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "wrong"},
            )
            assert invalid.status_code == 401

            login = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "secret"},
            )
            assert login.status_code == 200
            assert login.json()["token_type"] == "bearer"
            client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})

            authorized = client.post(
                "/api/projects/upload",
                files={"file": ("report.csv", b"invalid", "text/csv")},
            )
            assert authorized.status_code == 422
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()