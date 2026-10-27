import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import ratelimit
from app.db import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

PW = "correct-horse-battery"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    session.add(User(
        login_id="admin", password_hash=hash_password(PW), display_name="Admin",
        birth_month=1, birth_day=1, is_admin=True,
    ))
    session.commit()
    app.dependency_overrides[get_db] = lambda: session
    ratelimit.clear_all()
    yield session
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()


def make_client():
    return TestClient(app)


def login(client, login_id, pw=PW):
    response = client.post("/api/auth/login", json={"login_id": login_id, "password": pw})
    assert response.status_code == 200, response.text
    return {"x-csrf-token": response.json()["csrf_token"]}


@pytest.fixture()
def world(db):
    admin = make_client()
    admin_headers = login(admin, "admin")
    ids = {}
    for name in ("alice", "bob"):
        response = admin.post("/api/admin/friends", headers=admin_headers, json={
            "login_id": name, "password": PW, "display_name": name.title(),
            "birth_month": 5, "birth_day": 17, "timezone": "UTC", "theme": {"scene": "x"},
        })
        assert response.status_code == 201, response.text
        public_id = response.json()["public_id"]
        past = admin.post(f"/api/admin/friends/{public_id}/capsules", headers=admin_headers, json={
            "year": 2001, "content_type": "letter", "body": {"text": f"{name}-past"},
            "published": True,
        })
        future = admin.post(f"/api/admin/friends/{public_id}/capsules", headers=admin_headers, json={
            "year": 2199, "content_type": "letter", "body": {"text": f"{name}-SECRET"},
            "published": True,
        })
        assert past.status_code == 201 and future.status_code == 201
        ids[name] = {"pid": public_id, "past": past.json()["id"], "future": future.json()["id"]}
    return {"admin": admin, "admin_h": admin_headers, "ids": ids}
