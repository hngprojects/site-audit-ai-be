import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

# Mock the database session to avoid DATABASE_URL issues
@pytest.fixture
def client():
    with patch('app.platform.db.session.get_db', new_callable=AsyncMock):
        yield TestClient(app)

class TestForgetPassword:
    def test_forgot_password_success(self, client):
        """Test successful forgot password request"""
        with patch('app.features.auth.services.generate_reset_token', new_callable=AsyncMock) as mock_generate, \
             patch('app.features.auth.services.send_reset_email', new_callable=AsyncMock) as mock_send:

            mock_generate.return_value = ("test_token", "2025-11-18T12:00:00Z")

            response = client.post("/auth/forgot-password", json={"email": "test@example.com"})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "Password reset email sent" in data["message"]
            assert "expires in 1 minute" in data["message"]

    def test_forgot_password_invalid_email(self, client):
        """Test forgot password with invalid email"""
        response = client.post("/auth/forgot-password", json={"email": "invalid-email"})

        assert response.status_code == 422  # Pydantic validation error

    def test_resend_reset_token_success(self, client):
        """Test successful resend reset token"""
        with patch('app.features.auth.services.generate_reset_token', new_callable=AsyncMock) as mock_generate, \
             patch('app.features.auth.services.send_reset_email', new_callable=AsyncMock) as mock_send:

            mock_generate.return_value = ("new_test_token", "2025-11-18T12:00:00Z")

            response = client.post("/auth/resend-reset-token", json={"email": "test@example.com"})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "New password reset email sent" in data["message"]

    def test_reset_password_success(self, client):
        """Test successful password reset"""
        with patch('app.features.auth.services.verify_reset_token', new_callable=AsyncMock) as mock_verify, \
             patch('app.features.auth.services.update_password', new_callable=AsyncMock) as mock_update, \
             patch('app.features.auth.services.clear_reset_token', new_callable=AsyncMock) as mock_clear:

            response = client.post("/auth/reset-password", json={
                "email": "test@example.com",
                "token": "valid_token",
                "new_password": "newpassword123"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert data["message"] == "Password reset successfully"

    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token"""
        with patch('app.features.auth.services.verify_reset_token', new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = Exception("Invalid reset token")

            response = client.post("/auth/reset-password", json={
                "email": "test@example.com",
                "token": "invalid_token",
                "new_password": "newpassword123"
            })

            assert response.status_code == 500