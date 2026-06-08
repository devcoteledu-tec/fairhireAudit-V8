"""
tests/test_api.py — FairHire API integration tests

Uses FastAPI TestClient with a mocked database pool so no real
Supabase connection is needed in CI.

Run with:
    pytest tests/test_api.py -v
"""
import io
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# ── Mock the DB pool before api.py imports psycopg2 ──────────────────────────

@pytest.fixture(scope="session", autouse=True)
def mock_db_pool():
    """Patch psycopg2 pool so api.py never needs a real DB connection."""
    mock_conn   = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__  = MagicMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.getconn.return_value  = mock_conn
    mock_pool.putconn.return_value  = None

    with patch("psycopg2.pool.ThreadedConnectionPool", return_value=mock_pool):
        yield mock_pool, mock_conn, mock_cursor


@pytest.fixture(autouse=True)
def reset_mock_cursor(mock_db_pool):
    """Reset mock cursor state before every test to prevent cross-test pollution."""
    _, _, mock_cursor = mock_db_pool
    mock_cursor.reset_mock()
    mock_cursor.fetchone.side_effect  = None
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.execute.side_effect   = None


@pytest.fixture(scope="session")
def client(mock_db_pool):
    """Return a TestClient for the FastAPI app."""
    from api import app
    return TestClient(app, raise_server_exceptions=False)


# ── Helper: register + login to get a real JWT ───────────────────────────────

def _register_and_login(client, mock_cursor, email="ci@test.com", password="Test1234!"):
    """
    Mocks the DB responses for /api/register then /api/login,
    returning the JWT access_token.
    """
    import bcrypt
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Register: fetchone returns None (email not taken), then insert succeeds
    mock_cursor.fetchone.side_effect = [None, {"id": 1, "email": email,
                                                "company_name": "CI Corp",
                                                "plan": "free"}]
    res = client.post("/api/register", json={
        "email": email, "password": password, "company_name": "CI Corp"
    })
    assert res.status_code == 200, f"Register failed: {res.text}"

    # Login: fetchone returns the user row with hashed password
    mock_cursor.fetchone.side_effect = [{
        "id": 1, "email": email, "password_hash": hashed,
        "company_name": "CI Corp", "plan": "free",
        "email_verified": True
    }]
    res = client.post("/api/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.cookies.get("fh_access", "")


# ── /api/health ───────────────────────────────────────────────────────────────

def test_health_returns_200(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "version" in body


# ── /api/register ─────────────────────────────────────────────────────────────

def test_register_success(client, mock_db_pool):
    _, _, mock_cursor = mock_db_pool
    mock_cursor.fetchone.side_effect = [
        {"id": 99},   # RETURNING id from INSERT INTO users
    ]
    res = client.post("/api/register", json={
        "email": "new@test.com",
        "password": "Str0ng!Pass",
        "company_name": "X Corp"
    })
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "message" in body


def test_register_duplicate_email(client, mock_db_pool):
    _, _, mock_cursor = mock_db_pool
    # Simulate IntegrityError (duplicate email) — create_user returns None
    import psycopg2
    mock_cursor.execute.side_effect = psycopg2.IntegrityError("duplicate key")
    mock_cursor.side_effect = None
    res = client.post("/api/register", json={
        "email": "dupe@test.com",
        "password": "Str0ng!Pass",
        "company_name": "Dupe Corp"
    })
    mock_cursor.execute.side_effect = None   # reset for next test
    assert res.status_code == 200


def test_register_weak_password(client):
    res = client.post("/api/register", json={
        "email": "weak@test.com",
        "password": "abc",
        "company_name": "Weak Corp"
    })
    assert res.status_code == 400


# ── /api/login ────────────────────────────────────────────────────────────────

def test_login_success(client, mock_db_pool):
    import bcrypt
    _, _, mock_cursor = mock_db_pool
    pw = "Test1234!"
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    mock_cursor.fetchone.return_value = {
        "id": 1, "email": "ok@test.com", "password_hash": hashed,
        "company_name": "OK Corp", "plan": "free",
        "email_verified": True
    }
    res = client.post("/api/login", json={"email": "ok@test.com", "password": pw})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["email"] == "ok@test.com"
    assert "fh_access" in res.cookies


def test_login_wrong_password(client, mock_db_pool):
    import bcrypt
    _, _, mock_cursor = mock_db_pool
    hashed = bcrypt.hashpw(b"correct", bcrypt.gensalt()).decode()
    mock_cursor.fetchone.return_value = {
        "id": 1, "email": "x@test.com", "password_hash": hashed,
        "company_name": "X", "plan": "free"
    }
    res = client.post("/api/login", json={"email": "x@test.com", "password": "wrong"})
    assert res.status_code == 401


def test_login_unknown_email(client, mock_db_pool):
    _, _, mock_cursor = mock_db_pool
    mock_cursor.fetchone.return_value = None
    res = client.post("/api/login", json={"email": "ghost@test.com", "password": "Any1234!"})
    assert res.status_code == 401


# ── /api/history ──────────────────────────────────────────────────────────────

def test_history_requires_auth(client):
    res = client.get("/api/history")
    assert res.status_code == 401


def test_history_returns_list(client, mock_db_pool):
    _, _, mock_cursor = mock_db_pool
    token = _register_and_login(client, mock_cursor,
                                 email="hist@test.com", password="History1!")
    # Mock fetchall for history query
    mock_cursor.fetchall.return_value = [
        {"id": 1, "fair_hiring_score": 82.0, "score_label": "Good",
         "original_filename": "test.csv", "row_count": 200,
         "computed_at": "2025-01-01T10:00:00Z", "flags": [],
         "caste_flags": [], "skin_flags": [], "referral_flags": [],
         "proxy_flags": [], "marital_flags": [], "institution_flags": [],
         "age_flags": [], "module_results": {}}
    ]
    res = client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ── /api/audit ────────────────────────────────────────────────────────────────

def test_audit_requires_auth(client):
    csv_bytes = b"gender,shortlisted,hired\nMale,Yes,Yes\n"
    res = client.post("/api/audit",
                      files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")})
    assert res.status_code == 401


def test_audit_rejects_non_csv(client, mock_db_pool):
    import bcrypt
    _, _, mock_cursor = mock_db_pool
    token = _register_and_login(client, mock_cursor,
                                 email="audit@test.com", password="Audit1234!")
    res = client.post(
        "/api/audit",
        files={"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"}
    )
    # application/octet-stream with .exe extension — engine should reject on content check
    # (415 or 400 depending on implementation)
    assert res.status_code in (400, 415)


def test_audit_rejects_too_few_rows(client, mock_db_pool):
    _, _, mock_cursor = mock_db_pool
    token = _register_and_login(client, mock_cursor,
                                 email="fewrows@test.com", password="FewRows1!")
    tiny_csv = b"gender,shortlisted,hired\nMale,Yes,Yes\nFemale,Yes,No\n"
    res = client.post(
        "/api/audit",
        files={"file": ("tiny.csv", io.BytesIO(tiny_csv), "text/csv")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 400
    assert "row" in res.text.lower() or "insufficient" in res.text.lower()


def test_audit_valid_csv_returns_score(client, mock_db_pool):
    """End-to-end: a valid CSV with 200+ rows must return a fair_hiring_score."""
    _, _, mock_cursor = mock_db_pool
    token = _register_and_login(client, mock_cursor,
                                 email="valid@test.com", password="Valid1234!")

    # Build a minimal fair CSV with 200 rows
    lines = ["gender,shortlisted,hired"]
    for i in range(100):
        lines.append("Male,Yes,Yes" if i < 40 else "Male,Yes,No")
    for i in range(100):
        lines.append("Female,Yes,Yes" if i < 40 else "Female,Yes,No")
    csv_bytes = "\n".join(lines).encode()

    # Mock the INSERT for save_audit
    mock_cursor.fetchone.return_value = {"id": 42}

    res = client.post(
        "/api/audit",
        files={"file": ("valid.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    body = res.json()
    assert "fair_hiring_score" in body
    assert 0 <= body["fair_hiring_score"] <= 100
    assert "score_label" in body
    assert "flags" in body