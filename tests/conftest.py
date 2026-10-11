import os

# Configure the app BEFORE importing it: settings are read once at import time.
os.environ["SECRET_KEY"] = "test-secret-key-for-tests-only-0123456789abcdef"
os.environ["PASSWORD_ITERATIONS"] = "1000"  # fast hashing in tests
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

test_engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client():
    Base.metadata.create_all(test_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)


def register_and_login(client, email="alice@example.com", password="correct-horse-1"):
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", data={"username": email, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register_and_login(client)


@pytest.fixture
def other_auth(client):
    return register_and_login(client, "bob@example.com")


def make_app(client, auth, company="Acme", role="Data Engineer", **extra):
    resp = client.post("/applications", json={"company": company, "role": role, **extra}, headers=auth)
    assert resp.status_code == 201, resp.text
    return resp.json()
