from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_api_process_only():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"
