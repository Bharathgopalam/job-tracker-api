import jwt

from app.config import get_settings
from app.security import hash_password, verify_password
from conftest import register_and_login


def test_register_returns_user_without_password(client):
    resp = client.post("/auth/register", json={"email": "Alice@Example.com", "password": "password123"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"  # normalized to lowercase
    assert "password" not in body and "password_hash" not in body


def test_duplicate_email_conflicts_case_insensitively(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    resp = client.post("/auth/register", json={"email": "A@EXAMPLE.COM", "password": "password123"})
    assert resp.status_code == 409


def test_register_validation(client):
    assert client.post("/auth/register", json={"email": "a@example.com", "password": "short"}).status_code == 422
    assert client.post("/auth/register", json={"email": "not-an-email", "password": "password123"}).status_code == 422


def test_login_success_and_me(client):
    headers = register_and_login(client)
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200 and resp.json()["email"] == "alice@example.com"


def test_login_wrong_password_and_unknown_user(client):
    client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    bad_pw = client.post("/auth/login", data={"username": "a@example.com", "password": "wrong-password"})
    unknown = client.post("/auth/login", data={"username": "nobody@example.com", "password": "password123"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json() == unknown.json()  # no user enumeration


def test_protected_routes_require_a_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/applications").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_expired_and_forged_tokens_rejected(client):
    register_and_login(client)
    settings = get_settings()
    expired = jwt.encode({"sub": "1", "exp": 1}, settings.secret_key, algorithm=settings.algorithm)
    forged = jwt.encode({"sub": "1"}, "wrong-secret-wrong-secret-wrong-secret-12", algorithm=settings.algorithm)
    for token in (expired, forged):
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


def test_password_hashing_is_salted_and_verifiable():
    a, b = hash_password("password123"), hash_password("password123")
    assert a != b
    assert verify_password("password123", a)
    assert not verify_password("password124", a)
    assert not verify_password("password123", "garbage")


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
