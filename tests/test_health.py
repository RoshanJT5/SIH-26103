from fastapi.testclient import TestClient

from backend.app.db.session import get_db
from backend.app.main import app


def test_health_works_without_groq_credentials(migrated_database, monkeypatch):
    _, _, session_factory = migrated_database
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("GROQ_MODEL", "")

    from backend.app.core.config import get_settings

    get_settings.cache_clear()

    def override_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok", "assistant_enabled": False}
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

