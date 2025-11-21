import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status, HTTPException
from app.features.sites.services import site_service
from app.features.sites.models.site import Site

# Test Service
@pytest.mark.asyncio
async def test_delete_site_service_success():
    mock_db = AsyncMock()
    site_id = "site_123"
    user_id = "user_123"
    
    # Mock the site query result
    mock_site = Site(id=site_id, user_id=user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_site
    mock_db.execute.return_value = mock_result

    # Call the service
    result = await site_service.delete_site(mock_db, site_id, user_id)

    # Verify
    assert result is True
    mock_db.delete.assert_called_once_with(mock_site)
    mock_db.commit.assert_called_once()

@pytest.mark.asyncio
async def test_delete_site_service_not_found():
    mock_db = AsyncMock()
    site_id = "site_123"
    user_id = "user_123"
    
    # Mock the site query result to return None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    # Call the service and expect 404
    with pytest.raises(HTTPException) as exc:
        await site_service.delete_site(mock_db, site_id, user_id)
    
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_delete_site_service_forbidden():
    mock_db = AsyncMock()
    site_id = "site_123"
    user_id = "user_123"
    other_user_id = "user_456"
    
    # Mock the site query result to return site belonging to other user
    mock_site = Site(id=site_id, user_id=other_user_id)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_site
    mock_db.execute.return_value = mock_result

    # Call the service and expect 403
    with pytest.raises(HTTPException) as exc:
        await site_service.delete_site(mock_db, site_id, user_id)
    
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN

# Test Router (Integration-ish)
import sys
from unittest.mock import MagicMock

# Mock google module to avoid installation issues
mock_google = MagicMock()
sys.modules["google"] = mock_google
sys.modules["google.auth"] = mock_google
sys.modules["google.auth.transport"] = mock_google
sys.modules["google.auth.transport.requests"] = mock_google
sys.modules["google.oauth2"] = mock_google
sys.modules["google.oauth2.id_token"] = mock_google

from fastapi.testclient import TestClient
from app.main import app
from app.features.auth.routes.auth import get_current_user
from app.features.auth.models.user import User

client = TestClient(app)

# Mock user
mock_user = User(id="user_123", email="test@example.com")

async def mock_get_current_user():
    return mock_user

app.dependency_overrides[get_current_user] = mock_get_current_user

@patch("app.features.sites.services.site_service.delete_site")
def test_delete_site_endpoint_success(mock_delete_service):
    # Mock service to return True (async)
    mock_delete_service.return_value = True
    
    response = client.delete("/api/v1/sites/site_123")
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_delete_service.assert_called_once()

@patch("app.features.sites.services.site_service.delete_site")
def test_delete_site_endpoint_not_found(mock_delete_service):
    # Mock service to raise 404
    mock_delete_service.side_effect = HTTPException(status_code=404, detail="Site not found")
    
    response = client.delete("/api/v1/sites/site_123")
    
    assert response.status_code == status.HTTP_404_NOT_FOUND

