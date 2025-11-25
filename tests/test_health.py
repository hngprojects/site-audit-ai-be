def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status_code"] == 200
    assert payload["status"] == "success"
    assert payload["message"] == "Service is healthy"
    assert payload["data"] == {"status": "ok", "service": "Site Audit AI"}


def test_root_info(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "Site Audit AI API"
    assert payload["version"] == "1.0.0"
    assert payload["docs_url"] == "/docs"
    assert payload["api_base"] == "/api/v1"
