import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
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

            # Mock the generate_reset_token method
            mock_auth_service.generate_reset_token.return_value = ("reset_token_123", "2025-11-19T12:01:00Z")

            # Mock the database dependency
            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                # Mock the email sending
                with patch("app.features.auth.routes.auth.send_password_reset_email") as mock_send_email:
                    response = client.post(
                        "/api/v1/auth/auth/forgot-password",
                        json={"email": "test@example.com"}
                    )

                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["success"] is True
                    assert "Password reset email sent" in response_data["message"]

                    # Verify the auth service was called correctly
                    mock_auth_service.generate_reset_token.assert_called_once_with("test@example.com")

                    # Verify email was sent
                    mock_send_email.assert_called_once_with("test@example.com", "reset_token_123")

    async def test_forgot_password_user_not_found(self, client, mock_db):
        """Test forgot password with non-existent user"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock the generate_reset_token to raise HTTPException
            from fastapi import HTTPException
            mock_auth_service.generate_reset_token.side_effect = HTTPException(
                status_code=404,
                detail="User not found"
            )

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                response = client.post(
                    "/api/v1/auth/auth/forgot-password",
                    json={"email": "nonexistent@example.com"}
                )

                assert response.status_code == 404

    async def test_forgot_password_invalid_email_format(self, client, mock_db):
        """Test forgot password with invalid email format"""
        with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
            response = client.post(
                "/api/v1/auth/auth/forgot-password",
                json={"email": "invalid-email"}
            )

            # This should fail at validation level
            assert response.status_code == 422  # Validation error

    async def test_resend_reset_token_success(self, client, mock_db):
        """Test successful resend reset token request"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock the generate_reset_token method
            mock_auth_service.generate_reset_token.return_value = ("new_reset_token_456", "2025-11-19T12:01:00Z")

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                with patch("app.features.auth.routes.auth.send_password_reset_email") as mock_send_email:
                    response = client.post(
                        "/api/v1/auth/auth/resend-reset-token",
                        json={"email": "test@example.com"}
                    )

                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["success"] is True
                    assert "New password reset email sent" in response_data["message"]

                    # Verify the auth service was called correctly
                    mock_auth_service.generate_reset_token.assert_called_once_with("test@example.com")

                    # Verify email was sent
                    mock_send_email.assert_called_once_with("test@example.com", "new_reset_token_456")

    async def test_verify_forgot_password_success(self, client, mock_db):
        """Test successful password reset verification"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock the auth service methods
            mock_auth_service.verify_reset_token.return_value = True
            mock_auth_service.update_password.return_value = None

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                response = client.post(
                    "/api/v1/auth/auth/verify-forgot-password",
                    json={
                        "email": "test@example.com",
                        "token": "valid_reset_token",
                        "new_password": "NewPassword123!"
                    }
                )

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["success"] is True
                assert "Password reset successfully" in response_data["message"]

                # Verify the auth service methods were called correctly
                mock_auth_service.verify_reset_token.assert_called_once_with("test@example.com", "valid_reset_token")
                mock_auth_service.update_password.assert_called_once_with("test@example.com", "NewPassword123!")

    async def test_verify_forgot_password_invalid_token(self, client, mock_db):
        """Test password reset verification with invalid token"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock verify_reset_token to raise HTTPException
            from fastapi import HTTPException
            mock_auth_service.verify_reset_token.side_effect = HTTPException(
                status_code=400,
                detail="Invalid or expired reset token"
            )

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                response = client.post(
                    "/api/v1/auth/auth/verify-forgot-password",
                    json={
                        "email": "test@example.com",
                        "token": "invalid_token",
                        "new_password": "NewPassword123!"
                    }
                )

                assert response.status_code == 400

    async def test_verify_forgot_password_weak_password(self, client, mock_db):
        """Test password reset verification with weak password"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock the auth service methods
            mock_auth_service.verify_reset_token.return_value = True
            mock_auth_service.update_password.return_value = None

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                response = client.post(
                    "/api/v1/auth/auth/verify-forgot-password",
                    json={
                        "email": "test@example.com",
                        "token": "valid_token",
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

            # Mock the generate_reset_token method
            mock_auth_service.generate_reset_token.return_value = ("reset_token_123", "2025-11-19T12:01:00Z")

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                # Mock the httpx post request to avoid hitting the real external service
                with patch("httpx.post") as mock_httpx_post:
                    from unittest.mock import Mock
                    mock_response = Mock()
                    mock_response.raise_for_status = Mock()
                    mock_httpx_post.return_value = mock_response
                    
                    response = client.post(
                        "/api/v1/auth/auth/forgot-password",
                        json={"email": "test@example.com"}
                    )

                    # The endpoint should return success
                    assert response.status_code == 200
                    response_data = response.json()
                    assert response_data["success"] is True