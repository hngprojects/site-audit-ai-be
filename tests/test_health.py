from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status_code"] == 200
    assert payload["status"] == "success"
    assert payload["message"] == "Service is healthy"
    assert payload["data"] == {"status": "ok", "service": "Site Audit AI"}