import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app

client = TestClient(app)

def test_scrape_endpoint():
    response = client.post(
        "/api/v1/scraping/scrape",
        json={"url": "https://example.com"}
    )

    assert response.status_code == 200
    data = response.json()
    assert str(data["url"]) == "https://example.com/"
    assert data["title"] == "Example Domain"
    assert "Example Domain" in data["content_preview"]
