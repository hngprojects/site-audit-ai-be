# tests/test_rate_limit.py
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.platform.config import settings

@pytest.fixture(autouse=True)
def set_in_memory():
    # ensure in-memory store for testing
    settings.FORCE_IN_MEMORY_RATE_LIMITER = True
    yield

@pytest.mark.asyncio
async def test_waitlist_register_rate_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        # ensure under limit requests succeed
        limit = settings.WAITLIST_REGISTER_LIMIT
        for i in range(limit):
            r = await ac.post("/waitlist", json={"name": f"name{i}", "email": f"user{i}@example.com"})
            # Depending on your add_to_waitlist implementation this might return 200 or 201.
            # If your app requires DB, you may need to mock or adjust. For the test we'll
            # only assert that we don't get 429 until we exceed the limit.
            assert r.status_code != 429

        # one more should be rate-limited
        r = await ac.post("/waitlist", json={"name": "nameX", "email": "userX@example.com"})
        assert r.status_code == 429
        assert "Retry-After" in r.headers

@pytest.mark.asyncio
async def test_waitlist_stats_rate_limit_get():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        limit = settings.WAITLIST_STATS_LIMIT
        for i in range(limit):
            r = await ac.get("/waitlist/stats")
            assert r.status_code != 429
        r = await ac.get("/waitlist/stats")
        assert r.status_code == 429
