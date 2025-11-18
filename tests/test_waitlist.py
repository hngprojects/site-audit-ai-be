import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from app.features.waitlist.routes.waitlist import router
from app.features.waitlist.schemas.waitlist import WaitlistIn, WaitlistOut

@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.asyncio
async def test_join_waitlist_success(app):
    # Mock DB session and add_to_waitlist
    mock_db = AsyncMock()
    mock_entry = AsyncMock()
    mock_entry.id = 1
    mock_entry.name = "Alice"
    mock_entry.email = "alice@example.com"
    mock_entry.created_at = "2025-01-01T00:00:00"

    with patch("app.features.waitlist.routes.waitlist.add_to_waitlist", return_value=mock_entry):
        with patch("app.features.waitlist.routes.waitlist.send_thank_you_email") as mock_email:
            async with AsyncClient(app=app, base_url="http://test") as ac:
                response = await ac.post("/waitlist", json={"name": "Alice", "email": "alice@example.com"})

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Waitlist entry created"
    assert data["data"]["name"] == "Alice"
    assert data["data"]["email"] == "alice@example.com"
    mock_email.assert_called_once_with("alice@example.com", "Alice")


@pytest.mark.asyncio
async def test_join_waitlist_duplicate_email(app):
    mock_db = AsyncMock()
    # Raise Exception to simulate duplicate email
    with patch("app.features.waitlist.routes.waitlist.add_to_waitlist", side_effect=Exception("duplicate")):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.post("/waitlist", json={"name": "Alice", "email": "alice@example.com"})

    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Email already registered or DB error."


@pytest.mark.asyncio
async def test_waitlist_stats_success(app):
    stats_data = {
        "total_signups": 10,
        "signup_rate_per_hour_last_24h": 0.5
    }

    with patch("app.features.waitlist.routes.waitlist.get_waitlist_stats", return_value=stats_data):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            response = await ac.get("/waitlist/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Waitlist statistics retrieved"
    assert data["data"]["total_signups"] == 10
    assert data["data"]["signup_rate_per_hour_last_24h"] == 0.5
