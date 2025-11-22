import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.platform.db.session import get_db
from app.features.auth.models.user import User
from app.features.sites.models.site import Site
from app.features.auth.utils.security import hash_password
from app.features.auth.schemas.auth import LoginRequest


@pytest.fixture
async def test_db():
    """Override the database dependency for testing"""
    
    async for session in get_db():
        yield session


@pytest.fixture
async def test_user(test_db: AsyncSession):
    """Create a test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("TestPass123"),
        is_email_verified=True
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def auth_token(test_user, test_db: AsyncSession):
    """Get authentication token for test user"""
    from app.features.auth.services.auth_service import AuthService
    auth_service = AuthService(test_db)
    login_request = LoginRequest(email="test@example.com", password="TestPass123")
    token_response = await auth_service.login_user(login_request)
    return token_response.access_token


@pytest.fixture
async def test_site(test_user, test_db: AsyncSession):
    """Create a test site"""
    from app.features.sites.services.site import create_site_for_user
    from app.features.sites.schemas.site import SiteCreate

    site_data = SiteCreate(
        root_url="https://example.com",
        display_name="Test Site"
    )
    site = await create_site_for_user(test_db, test_user.id, site_data)
    return site


import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_site_success():
    """Test successful site update"""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # First, login to get token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]

        # Create a site
        create_response = await client.post(
            "/api/v1/sites",
            json={
                "root_url": "https://example.com",
                "display_name": "Test Site"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert create_response.status_code == 201
        site_id = create_response.json()["data"]["id"]

        # Update the site
        update_data = {
            "display_name": "Updated Test Site",
            "status": "archived"
        }
        update_response = await client.put(
            f"/api/v1/sites/{site_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["status_code"] == 200
        assert data["status"] == "success"
        assert data["message"] == "Site updated successfully"
        assert data["data"]["display_name"] == "Updated Test Site"
        assert data["data"]["status"] == "archived"
        assert data["data"]["id"] == site_id


@pytest.mark.asyncio
async def test_update_site_not_found():
    """Test updating non-existent site"""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Login first
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]

        # Try to update non-existent site
        update_response = await client.put(
            "/api/v1/sites/019aa91e-0000-0000-0000-000000000000",
            json={"display_name": "Updated Site"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert update_response.status_code == 404
        data = update_response.json()
        assert data["status_code"] == 404
        assert "not found" in data["message"].lower()


@pytest.mark.asyncio
async def test_update_site_unauthorized():
    """Test updating site without authentication"""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        update_response = await client.put(
            "/api/v1/sites/019aa91e-0000-0000-0000-000000000000",
            json={"display_name": "Updated Site"}
        )

        assert update_response.status_code == 403  # API returns 403 for unauthenticated


@pytest.mark.asyncio
async def test_update_site_no_fields():
    """Test updating site with no fields provided"""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Login and create site
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123"
            }
        )
        token = login_response.json()["data"]["access_token"]

        create_response = await client.post(
            "/api/v1/sites",
            json={
                "root_url": "https://example2.com",
                "display_name": "Test Site 2"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        site_id = create_response.json()["data"]["id"]

        # Try to update with empty data
        update_response = await client.put(
            f"/api/v1/sites/{site_id}",
            json={},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert update_response.status_code == 400
        data = update_response.json()
        assert data["status_code"] == 400
        assert "no fields to update" in data["message"].lower()


@pytest.mark.asyncio
async def test_update_site_partial():
    """Test partial site update (only one field)"""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Login and create site
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass123"
            }
        )
        token = login_response.json()["data"]["access_token"]

        create_response = await client.post(
            "/api/v1/sites",
            json={
                "root_url": "https://example3.com",
                "display_name": "Test Site 3"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        site_id = create_response.json()["data"]["id"]

        # Update only display_name
        update_response = await client.put(
            f"/api/v1/sites/{site_id}",
            json={"display_name": "Partially Updated Site"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["data"]["display_name"] == "Partially Updated Site"
        assert data["data"]["status"] == "active"  # Should remain unchanged