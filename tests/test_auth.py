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


def test_user_signup_and_protected_routing():
    with TestClient(app) as client:
        # 1. Routes discovery is public
        routes_res = client.get("/api/auth/routes")
        assert routes_res.status_code == 200
        routes_data = routes_res.json()
        assert "/dashboard" in routes_data["protected"]["frontend_pages"]
        assert "/" in routes_data["public"]["frontend_pages"]
        assert "/faq" in routes_data["public"]["frontend_pages"]

        # 2. Accessing protected endpoint without token returns 401
        unauthed_check = client.get("/api/auth/check-protected")
        assert unauthed_check.status_code == 401

        unauthed_me = client.get("/api/auth/me")
        assert unauthed_me.status_code == 401

        # 3. User signup creates account and returns token
        signup_res = client.post(
            "/api/auth/signup",
            json={
                "name": "Test Officer",
                "email": "test.officer@gov.in",
                "password": "pass1234password",
                "username": "test_officer",
            },
        )
        assert signup_res.status_code == 200
        data = signup_res.json()
        token = data["access_token"]
        assert token
        assert data["user"]["email"] == "test.officer@gov.in"

        # 4. Authenticated request succeeds
        authed_client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
        me_res = authed_client.get("/api/auth/me")
        assert me_res.status_code == 200
        assert me_res.json()["name"] == "Test Officer"

        check_res = authed_client.get("/api/auth/check-protected")
        assert check_res.status_code == 200
        assert check_res.json()["authenticated"] is True

        # 5. User login with registered credentials succeeds
        login_res = client.post(
            "/api/auth/login",
            json={
                "username": "test.officer@gov.in",
                "password": "pass1234password",
            },
        )
        assert login_res.status_code == 200
        assert login_res.json()["user"]["email"] == "test.officer@gov.in"


def test_public_and_protected_page_routing():
    with TestClient(app) as client:
        # Public pages can be visited without authentication
        for pub_path in ["/", "/faq", "/help", "/documents", "/login", "/signup"]:
            res = client.get(pub_path)
            assert res.status_code == 200
            assert res.json()["access"] == "public"

        # Protected pages redirect to /login when unauthenticated
        for prot_path in ["/dashboard", "/monitoring", "/projects", "/analytics", "/simulation", "/early-warnings"]:
            res = client.get(prot_path, follow_redirects=False)
            assert res.status_code == 307
            loc = res.headers.get("location", "")
            assert "/login?redirect=" in loc
            assert "reason=auth_required" in loc

        # Verify route API for unauthenticated client
        res_check_faq = client.get("/api/auth/verify-route?route=/faq")
        assert res_check_faq.status_code == 200
        assert res_check_faq.json()["allowed"] is True
        assert res_check_faq.json()["is_protected"] is False

        res_check_dash = client.get("/api/auth/verify-route?route=/dashboard")
        assert res_check_dash.status_code == 200
        assert res_check_dash.json()["allowed"] is False
        assert res_check_dash.json()["is_protected"] is True
        assert "/login?redirect=" in res_check_dash.json()["redirect_url"]

        # Dashboard entry unauthenticated returns redirect advice
        entry_res = client.get("/api/auth/dashboard-entry")
        assert entry_res.status_code == 200
        assert entry_res.json()["allowed"] is False
        assert "/login" in entry_res.json()["destination"]

        # Log in to acquire an authenticated session
        signup_res = client.post(
            "/api/auth/signup",
            json={
                "name": "Routing Officer",
                "email": "routing.officer@gov.in",
                "password": "officerpassword123",
            },
        )
        token = signup_res.json()["access_token"]
        authed_client = TestClient(app, headers={"Authorization": f"Bearer {token}"})

        # Protected pages now grant access directly to authenticated officer
        for prot_path in ["/dashboard", "/monitoring", "/projects", "/analytics"]:
            res = authed_client.get(prot_path, follow_redirects=False)
            assert res.status_code == 200
            assert res.json()["access"] == "granted"
            assert res.json()["authenticated"] is True

        # Verify route API for authenticated client
        dash_verify = authed_client.get("/api/auth/verify-route?route=/dashboard")
        assert dash_verify.status_code == 200
        assert dash_verify.json()["allowed"] is True
        assert dash_verify.json()["is_protected"] is True
        assert dash_verify.json()["user"]["email"] == "routing.officer@gov.in"

        # Dashboard entrypoint routes authenticated user to dashboard
        entry_authed = authed_client.get("/api/auth/dashboard-entry")
        assert entry_authed.status_code == 200
        assert entry_authed.json()["allowed"] is True
        assert entry_authed.json()["destination"] == "/dashboard"


def test_user_persisted_in_database():
    from backend.app.db.session import SessionLocal
    from backend.app.models.user import User

    unique_email = "db.officer@gov.in"
    with TestClient(app) as client:
        # 1. Sign up via backend API
        signup_res = client.post(
            "/api/auth/signup",
            json={
                "name": "Database Officer",
                "email": unique_email,
                "password": "db_secure_password_123",
                "username": "db_officer",
            },
        )
        assert signup_res.status_code == 200

        # 2. Query SQL Database directly to verify the record was saved in database
        db = SessionLocal()
        try:
            db_record = db.query(User).filter_by(email=unique_email).first()
            assert db_record is not None
            assert db_record.name == "Database Officer"
            assert db_record.username == "db_officer"
            assert db_record.password_hash != "db_secure_password_123"  # Securely hashed
            assert db_record.role == "officer"
        finally:
            db.close()

        # 3. Authenticate against database on login
        login_res = client.post(
            "/api/auth/login",
            json={
                "username": unique_email,
                "password": "db_secure_password_123",
            },
        )
        assert login_res.status_code == 200
        assert login_res.json()["user"]["email"] == unique_email


def test_profile_update_persists_in_db_and_across_relogin():
    from backend.app.db.session import SessionLocal
    from backend.app.models.user import User

    unique_email = "relogin.officer@gov.in"
    password = "persisted_pass_123"

    with TestClient(app) as client:
        # 1. User signs up with original name and username
        signup_res = client.post(
            "/api/auth/signup",
            json={
                "name": "Original Name",
                "email": unique_email,
                "password": password,
                "username": "orig_username",
            },
        )
        assert signup_res.status_code == 200
        token = signup_res.json()["access_token"]
        assert signup_res.json()["user"]["name"] == "Original Name"
        assert signup_res.json()["user"]["username"] == "orig_username"

        authed_client = TestClient(app, headers={"Authorization": f"Bearer {token}"})

        # 2. Update profile with new name and new username
        update_res = authed_client.put(
            "/api/auth/me",
            json={
                "name": "Updated Full Name",
                "username": "new_awesome_username",
                "email": unique_email,
            },
        )
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Updated Full Name"
        assert update_res.json()["username"] == "new_awesome_username"

        # 3. GET /api/auth/me immediately reflects changes
        me_res = authed_client.get("/api/auth/me")
        assert me_res.status_code == 200
        assert me_res.json()["name"] == "Updated Full Name"
        assert me_res.json()["username"] == "new_awesome_username"

        # 4. Directly query database to guarantee persistence in SQL table
        db = SessionLocal()
        try:
            db_user = db.query(User).filter_by(email=unique_email).first()
            assert db_user is not None
            assert db_user.name == "Updated Full Name"
            assert db_user.username == "new_awesome_username"
        finally:
            db.close()

        # 5. User logs out (represented by discarding previous token) and logs back in with the NEW username
        new_login_res = client.post(
            "/api/auth/login",
            json={
                "username": "new_awesome_username",
                "password": password,
            },
        )
        assert new_login_res.status_code == 200
        logged_in_user = new_login_res.json()["user"]
        # Must show the NEW name, not the old name!
        assert logged_in_user["name"] == "Updated Full Name"
        assert logged_in_user["username"] == "new_awesome_username"

        # 6. Also verify logging in with email returns the new name and username
        email_login_res = client.post(
            "/api/auth/login",
            json={
                "username": unique_email,
                "password": password,
            },
        )
        assert email_login_res.status_code == 200
        assert email_login_res.json()["user"]["name"] == "Updated Full Name"
        assert email_login_res.json()["user"]["username"] == "new_awesome_username"