import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app

client = TestClient(app)

def test_scrape_endpoint():
    # Mock the selenium_service instance
    with patch("app.features.scraping.routes.scraping_routes.selenium_service") as mock_service:
        mock_service.scrape_url.return_value = {
            "url": "https://example.com/",
            "title": "Example Domain",
            "content_preview": "This is a test content preview."
        }

        response = client.post(
            "/api/v1/scraping/scrape",
            json={"url": "https://example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert str(data["url"]) == "https://example.com/"
        assert data["title"] == "Example Domain"
        assert data["content_preview"] == "This is a test content preview."
