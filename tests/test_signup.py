import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

def test_signup_success():
    """Test successful user signup."""
    # Patching the email sending function at the point where it's called
    with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send_email:
        mock_send_email.return_value = None
        
        # Use unique email and username to avoid conflicts with previous test runs
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "email": f"testuser{unique_id}@example.com",
            "username": f"testuser{unique_id}",
            "password": "TestPassword123"
        }
        response = client.post("/api/v1/auth/signup", json=payload)
        
        # Check response
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
        data = response.json()
        assert "message" in data
        assert "registered successfully" in data["message"].lower()
        
        # Verify the response contains user data and tokens
        assert "data" in data
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        
        # Verify email was supposed to be sent
        mock_send_email.assert_called_once()
