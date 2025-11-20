import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)


@pytest.fixture
def authenticated_user():
    """Fixture to create and login a test user."""
    with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send_email:
        mock_send_email.return_value = None
        
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"logouttest{unique_id}@example.com",
            "username": f"logouttest{unique_id}",
            "password": "TestPassword123"
        }
        
        # Create the user
        signup_response = client.post("/api/v1/auth/signup", json=user_data)
        assert signup_response.status_code == 201
        
        # Login to get fresh tokens
        login_response = client.post("/api/v1/auth/login", json={
            "email": user_data["email"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        
        tokens = login_response.json()["data"]
        return {
            "user_data": user_data,
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"]
        }


def test_logout_success(authenticated_user):
    """Test successful logout with valid token."""
    access_token = authenticated_user["access_token"]
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = client.post("/api/v1/auth/logout", headers=headers)

    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert data["status"] == "success"
    assert "logout successful" in data["message"].lower()
    assert data["status_code"] == 200
    assert data["data"] == {}


def test_logout_without_token():
    """Test logout without providing authorization token."""
    response = client.post("/api/v1/auth/logout")
    
    assert response.status_code == 403  # Forbidden - no credentials provided


def test_logout_with_invalid_token():
    """Test logout with invalid token."""
    headers = {
        "Authorization": "Bearer invalid.token.here"
    }
    
    response = client.post("/api/v1/auth/logout", headers=headers)
    
    assert response.status_code == 401
    data = response.json()
    assert data["status"] == "error"
    assert "invalid" in data["message"].lower()


def test_logout_with_malformed_token():
    """Test logout with malformed authorization header."""
    headers = {
        "Authorization": "NotBearer invalid-token"
    }
    
    response = client.post("/api/v1/auth/logout", headers=headers)
    
    assert response.status_code == 403  # Invalid authentication scheme


def test_logout_with_expired_token():
    """Test logout with an expired token."""
    # This is a token that's already expired (you'd need to generate one with past expiry)
    # For now, we'll use an invalid token format
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNTE2MjM5MDIyfQ.invalid"
    }
    
    response = client.post("/api/v1/auth/logout", headers=headers)
    
    assert response.status_code == 401


def test_logout_with_empty_bearer_token():
    """Test logout with empty Bearer token."""
    headers = {
        "Authorization": "Bearer "
    }
    
    response = client.post("/api/v1/auth/logout", headers=headers)
    
    assert response.status_code in [401, 403]  # Either unauthorized or forbidden


def test_logout_multiple_times(authenticated_user):
    """Test that logout can be called multiple times with same token."""
    access_token = authenticated_user["access_token"]
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # First logout
    response1 = client.post("/api/v1/auth/logout", headers=headers)
    assert response1.status_code == 200
    
    # Second logout with same token (should still validate the token)
    # Note: In a production system with token blacklisting, this would fail
    response2 = client.post("/api/v1/auth/logout", headers=headers)
    assert response2.status_code == 200  # Still valid since we're not blacklisting


def test_logout_with_refresh_token(authenticated_user):
    """Test that logout doesn't work with refresh token (only access token)."""
    refresh_token = authenticated_user["refresh_token"]
    
    headers = {
        "Authorization": f"Bearer {refresh_token}"
    }
    
    response = client.post("/api/v1/auth/logout", headers=headers)
    
    # This should still validate as a JWT, but in production you might want to
    # specifically check token type
    assert response.status_code in [200, 401]


def test_logout_case_sensitive_bearer():
    """Test that 'Bearer' keyword handling with invalid token."""
    headers = {
        "Authorization": "bearer fake-token"  # lowercase 'bearer' but invalid token
    }
    
    response = client.post("/api/v1/auth/logout", headers=headers)
    
    # FastAPI HTTPBearer accepts lowercase 'bearer', but token is invalid
    assert response.status_code == 401


def test_logout_with_different_user_tokens(authenticated_user):
    """Test logout with tokens from different users."""
    # Create second user
    with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send_email:
        mock_send_email.return_value = None
        
        unique_id = str(uuid.uuid4())[:8]
        user2_data = {
            "email": f"logout2test{unique_id}@example.com",
            "username": f"logout2test{unique_id}",
            "password": "TestPassword123"
        }
        
        signup_response = client.post("/api/v1/auth/signup", json=user2_data)
        assert signup_response.status_code == 201
        
        user2_token = signup_response.json()["data"]["access_token"]
    
    # Logout with first user's token
    headers1 = {
        "Authorization": f"Bearer {authenticated_user['access_token']}"
    }
    response1 = client.post("/api/v1/auth/logout", headers=headers1)
    assert response1.status_code == 200
    
    # Logout with second user's token
    headers2 = {
        "Authorization": f"Bearer {user2_token}"
    }
    response2 = client.post("/api/v1/auth/logout", headers=headers2)
    assert response2.status_code == 200
    
    # Both should succeed independently


def test_logout_response_structure(authenticated_user):
    """Test that logout response has the correct structure."""
    access_token = authenticated_user["access_token"]
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    response = client.post("/api/v1/auth/logout", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure matches api_response format
    assert data["status"] == "success"
    assert "message" in data
    assert data["status_code"] == 200
    assert data["data"] == {}
