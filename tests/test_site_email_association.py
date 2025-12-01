import asyncio
import pytest
from fastapi.testclient import TestClient

from app.platform.db.session import SessionLocal, engine
from app.platform.db.base import Base


@pytest.fixture(scope="module", autouse=True)
def create_db_schema():
    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(_create())


@pytest.fixture(scope="function")
def auth_override(test_app):
    from app.features.sites.dependencies.site import get_owner_context

    def fake_owner():
        return {"user_id": "test-user"}

    test_app.dependency_overrides[get_owner_context] = fake_owner
    yield
    test_app.dependency_overrides.pop(get_owner_context, None)


async def _create_site_for_user(root_url: str = "https://example.com") -> str:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.features.sites.models.site import Site
    async with SessionLocal() as db:  # type: AsyncSession
        site = Site(user_id="test-user", root_url=root_url)
        db.add(site)
        await db.commit()
        await db.refresh(site)
        return str(site.id)


def test_associate_email_success(client: TestClient, auth_override):
    from app.platform.services import email as email_service

    sent = {}

    def fake_send_email(to, subject, body):
        sent["to"] = to
        sent["subject"] = subject
        sent["body"] = body

    # Monkeypatch email sending
    original_send = email_service.send_email
    email_service.send_email = fake_send_email
    try:
        site_id = asyncio.get_event_loop().run_until_complete(_create_site_for_user())

        resp = client.post(f"/api/v1/sites/{site_id}/emails", json={"email": "user@example.com"})
        assert resp.status_code in (200, 201)
        payload = resp.json()
        assert payload["status"] == "success"
        assert payload["data"]["site_id"] == site_id
        assert payload["data"]["email"] == "user@example.com"
        # Email was attempted
        assert sent.get("to") == "user@example.com"
    finally:
        email_service.send_email = original_send


def test_associate_email_duplicate_is_idempotent(client: TestClient, auth_override):
    site_id = asyncio.get_event_loop().run_until_complete(_create_site_for_user("https://dup.com"))
    first = client.post(f"/api/v1/sites/{site_id}/emails", json={"email": "dup@example.com"})
    assert first.status_code in (200, 201)
    second = client.post(f"/api/v1/sites/{site_id}/emails", json={"email": "dup@example.com"})
    assert second.status_code == 200
    payload = second.json()
    assert payload["message"] == "Email already associated"


def test_associate_email_invalid_email(client: TestClient, auth_override):
    site_id = asyncio.get_event_loop().run_until_complete(_create_site_for_user("https://bademail.com"))
    resp = client.post(f"/api/v1/sites/{site_id}/emails", json={"email": "not-an-email"})
    assert resp.status_code == 422


def test_associate_email_site_not_found(client: TestClient, auth_override):
    resp = client.post(f"/api/v1/sites/does-not-exist/emails", json={"email": "x@example.com"})
    assert resp.status_code in (404, 400)
