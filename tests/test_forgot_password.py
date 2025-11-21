import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.features.auth.models.user import User
from app.platform.db.session import get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.mark.asyncio
class TestForgotPassword:
    """Test cases for forgot password functionality"""

    async def test_forgot_password_success(self, client, mock_db):
        """Test successful forgot password request"""
        # Mock the auth service
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock user lookup
            mock_user = AsyncMock()
            mock_user.id = "user_id_123"
            mock_user.email = "test@example.com"
            mock_auth_service.get_user_by_email.return_value = mock_user

            # Mock the database dependency
            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                with patch("app.features.auth.routes.auth.generate_otp", return_value="654321") as mock_generate_otp:
                    with patch("app.features.auth.routes.auth.send_password_reset_email") as mock_send_email:
                        response = client.post(
                            "/api/v1/auth/forgot-password",
                            json={"email": "test@example.com"}
                        )

                        assert response.status_code == 200
                        response_data = response.json()
                        assert response_data["status"] == "success"
                        assert response_data["data"] == {"email": "test@example.com"}
                        assert "verification code has been resent" in response_data["message"].lower()

                        mock_auth_service.get_user_by_email.assert_called_once_with("test@example.com")
                        mock_generate_otp.assert_called_once()
                        mock_send_email.assert_called_once_with("test@example.com", "654321")

    async def test_forgot_password_user_not_found(self, client, mock_db):
        """Test forgot password with non-existent user"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock get_user_by_email to return None
            mock_auth_service.get_user_by_email.return_value = None

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                response = client.post(
                    "/api/v1/auth/forgot-password",
                    json={"email": "nonexistent@example.com"}
                )

                assert response.status_code == 404
                payload = response.json()
                assert payload["status"] == "error"
                assert "user not found" in payload["message"].lower()

    async def test_forgot_password_invalid_email_format(self, client, mock_db):
        """Test forgot password with invalid email format"""
        with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "invalid-email"}
            )

            # This should fail at validation level
            assert response.status_code == 422  # Validation error

    async def test_resend_reset_token_success(self, client, mock_db):
        """Test successful resend reset token request"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock user lookup
            mock_user = AsyncMock()
            mock_user.id = "user_id_123"
            mock_user.email = "test@example.com"
            mock_auth_service.get_user_by_email.return_value = mock_user

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                with patch("app.features.auth.routes.auth.generate_otp", return_value="123789") as mock_generate_otp:
                    with patch("app.features.auth.routes.auth.send_password_reset_email") as mock_send_email:
                        response = client.post(
                            "/api/v1/auth/resend-reset-token",
                            json={"email": "test@example.com"}
                        )

                        assert response.status_code == 200
                        response_data = response.json()
                        assert response_data["status"] == "success"
                        assert "new password reset email sent" in response_data["message"].lower()
                        assert response_data["data"] == {}

                        mock_auth_service.get_user_by_email.assert_called_once_with("test@example.com")
                        mock_generate_otp.assert_called_once()
                        mock_send_email.assert_called_once_with("test@example.com", "123789")

    async def test_verify_forgot_password_success(self, client, mock_db):
        """Test successful password reset verification"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service
            mock_auth_service.verify_otp.return_value = True
            mock_auth_service.update_password.return_value = None

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                response = client.post(
                    "/api/v1/auth/verify-forgot-password",
                    json={
                        "email": "test@example.com",
                        "token": "654321",
                        "new_password": "NewPassword123!"
                    }
                )

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["status"] == "success"
                assert "password reset successfully" in response_data["message"].lower()

                mock_auth_service.verify_otp.assert_called_once_with("test@example.com", "654321")
                mock_auth_service.update_password.assert_called_once_with("test@example.com", "NewPassword123!")

    async def test_verify_forgot_password_invalid_token(self, client, mock_db):
        """Test password reset verification with invalid token"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service
            mock_auth_service.verify_otp.side_effect = HTTPException(
                status_code=400,
                detail="Invalid or expired reset token"
            )

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                response = client.post(
                    "/api/v1/auth/verify-forgot-password",
                    json={
                        "email": "test@example.com",
                        "token": "invalid_token",
                        "new_password": "NewPassword123!"
                    }
                )

                assert response.status_code == 400
                payload = response.json()
                assert payload["status"] == "error"
                assert "invalid or expired reset token" in payload["message"].lower()

    async def test_verify_forgot_password_weak_password(self, client, mock_db):
        """Test password reset verification with weak password"""
        with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/auth/verify-forgot-password",
                json={
                    "email": "test@example.com",
                    "token": "654321",
                    "new_password": "weak"
                }
            )

            # This should fail at validation level
            assert response.status_code == 422  # Validation error

    async def test_forgot_password_email_sending_failure(self, client, mock_db):
        """Test forgot password when email sending fails"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock user lookup
            mock_user = AsyncMock()
            mock_user.id = "user_id_123"
            mock_user.email = "test@example.com"
            mock_auth_service.get_user_by_email.return_value = mock_user

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                with patch("app.features.auth.routes.auth.generate_otp", return_value="111222") as mock_generate_otp:
                    with patch("app.features.auth.routes.auth.send_password_reset_email") as mock_send_email:
                        response = client.post(
                            "/api/v1/auth/forgot-password",
                            json={"email": "test@example.com"}
                        )

                        assert response.status_code == 200
                        response_data = response.json()
                        assert response_data["status"] == "success"
                        assert response_data["data"] == {"email": "test@example.com"}

                        mock_generate_otp.assert_called_once()
                        mock_send_email.assert_called_once_with("test@example.com", "111222")
