# tests/test_rate_limit.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.platform.config import settings


@pytest.fixture(autouse=True)
def set_in_memory():
    """Force in-memory rate limiter for testing."""
    settings.FORCE_IN_MEMORY_RATE_LIMITER = True
    yield


@pytest.mark.asyncio
async def test_waitlist_register_rate_limit():
    limit = settings.RATE_LIMITS["/waitlist"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        # Requests under limit should succeed
        for i in range(limit):
            res = await ac.post(
                "/waitlist",
                json={"name": f"name{i}", "email": f"user{i}@example.com"},
            )
            assert res.status_code != 429

        # Next request should be blocked
        res = await ac.post(
            "/waitlist",
            json={"name": "overflow", "email": "overflow@example.com"},
        )
        assert res.status_code == 429
        assert "Retry-After" in res.headers


@pytest.mark.asyncio
async def test_waitlist_stats_rate_limit():
    limit = settings.RATE_LIMITS["/waitlist/stats"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        # Requests within limit are OK
        for _ in range(limit):
            res = await ac.get("/waitlist/stats")
            assert res.status_code != 429

        # Next request should be blocked
        res = await ac.get("/waitlist/stats")
        assert res.status_code == 429
