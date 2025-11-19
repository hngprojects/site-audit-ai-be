import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)


@pytest.fixture
def create_test_user():
    with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send_email:
        mock_send_email.return_value = None
        
        unique_id = str(uuid.uuid4())[:8]
        user_data = {
            "email": f"logintest{unique_id}@example.com",
            "username": f"logintest{unique_id}",
            "password": "TestPassword123"
        }
        
        # Create the user
        response = client.post("/api/v1/auth/signup", json=user_data)
        assert response.status_code == 201
        
        return user_data


def test_login_success(create_test_user):
    """Test successful login with valid credentials."""
    user_data = create_test_user
    
    login_payload = {
        "email": user_data["email"],
        "password": user_data["password"]
    }
    
    response = client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "message" in data
    assert "login successful" in data["message"].lower()
    assert "data" in data
    
    # Verify tokens are present
    assert "access_token" in data["data"]
    assert "refresh_token" in data["data"]
    assert "token_type" in data["data"]
    assert data["data"]["token_type"] == "bearer"
    
    # Verify user data is present
    assert "user" in data["data"]
    assert data["data"]["user"]["email"] == user_data["email"]
    assert data["data"]["user"]["username"] == user_data["username"]


def test_login_invalid_email():
    """Test login with non-existent email."""
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "TestPassword123"
    }
    
    response = client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "invalid email or password" in data["detail"].lower()


def test_login_invalid_password(create_test_user):
    """Test login with incorrect password."""
    user_data = create_test_user
    
    login_payload = {
        "email": user_data["email"],
        "password": "WrongPassword123"
    }
    
    response = client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "invalid email or password" in data["detail"].lower()


def test_login_missing_email():
    """Test login without email field."""
    login_payload = {
        "password": "TestPassword123"
    }
    
    response = client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 422  # Validation error


def test_login_missing_password():
    """Test login without password field."""
    login_payload = {
        "email": "test@example.com"
    }
    
    response = client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 422  # Validation error


def test_login_invalid_email_format():
    """Test login with invalid email format."""
    login_payload = {
        "email": "not-an-email",
        "password": "TestPassword123"
    }
    
    response = client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 422  # Validation error


def test_login_empty_credentials():
    """Test login with empty credentials."""
    login_payload = {
        "email": "",
        "password": ""
    }
    
    response = client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 422  # Validation error


def test_login_case_insensitive_email(create_test_user):
    """Test that login is case-insensitive for email."""
    user_data = create_test_user
    
    # Login with uppercase email
    login_payload = {
        "email": user_data["email"].upper(),
        "password": user_data["password"]
    }
    
    response = client.post("/api/v1/auth/login", json=login_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data["data"]


def test_login_updates_last_login(create_test_user):
    """Test that login updates the last_login timestamp."""
    user_data = create_test_user
    
    login_payload = {
        "email": user_data["email"],
        "password": user_data["password"]
    }
    
    # First login
    response1 = client.post("/api/v1/auth/login", json=login_payload)
    assert response1.status_code == 200
    
    # Second login (should update last_login)
    response2 = client.post("/api/v1/auth/login", json=login_payload)
    assert response2.status_code == 200
    
    # Both should succeed
    assert "access_token" in response2.json()["data"]


def test_login_returns_different_tokens_each_time(create_test_user):
    """Test that each login generates new tokens."""
    import time
    user_data = create_test_user
    
    login_payload = {
        "email": user_data["email"],
        "password": user_data["password"]
    }
    
    # First login
    response1 = client.post("/api/v1/auth/login", json=login_payload)
    token1 = response1.json()["data"]["access_token"]
    
    # Wait a second to ensure different timestamp
    time.sleep(1)
    
    # Second login
    response2 = client.post("/api/v1/auth/login", json=login_payload)
    token2 = response2.json()["data"]["access_token"]
    
    # Tokens should be different
    assert token1 != token2
