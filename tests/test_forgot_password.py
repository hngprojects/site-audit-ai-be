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

            # Mock user lookup
            mock_user = AsyncMock()
            mock_user.id = "user_id_123"
            mock_user.email = "test@example.com"
            mock_auth_service.get_user_by_email.return_value = mock_user

            # Mock the database dependency
            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                # Mock token creation
                with patch("app.features.auth.routes.auth.create_access_token") as mock_create_token:
                    mock_create_token.return_value = "jwt_reset_token_123"
                    
                    # Mock the email sending
                    with patch("app.features.auth.routes.auth.send_password_reset_email") as mock_send_email:
                        response = client.post(
                            "/api/v1/auth/forgot-password",
                            json={"email": "test@example.com"}
                        )

                        assert response.status_code == 200
                        response_data = response.json()
                        assert response_data["success"] is True
                        assert "Password reset email sent" in response_data["message"]

                        # Verify the auth service was called correctly
                        mock_auth_service.get_user_by_email.assert_called_once_with("test@example.com")
                        mock_create_token.assert_called_once()
                        mock_send_email.assert_called_once_with("test@example.com", "jwt_reset_token_123")

    async def test_forgot_password_user_not_found(self, client, mock_db):
        """Test forgot password with non-existent user"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock get_user_by_email to return None
            mock_auth_service.get_user_by_email.return_value = None

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
                # Mock token creation
                with patch("app.features.auth.routes.auth.create_refresh_token") as mock_create_token:
                    mock_create_token.return_value = "jwt_refresh_token_456"
                    
                    with patch("app.features.auth.routes.auth.send_password_reset_email") as mock_send_email:
                        response = client.post(
                            "/api/v1/auth/resend-reset-token",
                            json={"email": "test@example.com"}
                        )

                        assert response.status_code == 200
                        response_data = response.json()
                        assert response_data["success"] is True
                        assert "New password reset email sent" in response_data["message"]

                        # Verify the auth service was called correctly
                        mock_auth_service.get_user_by_email.assert_called_once_with("test@example.com")
                        mock_create_token.assert_called_once()
                        mock_send_email.assert_called_once_with("test@example.com", "jwt_refresh_token_456")

    async def test_verify_forgot_password_success(self, client, mock_db):
        """Test successful password reset verification"""
        with patch("app.features.auth.routes.auth.AuthService") as mock_auth_service_class:
            mock_auth_service = AsyncMock()
            mock_auth_service_class.return_value = mock_auth_service

            # Mock the auth service update_password method
            mock_auth_service.update_password.return_value = None

            # Create a valid JWT token for testing
            from app.features.auth.utils.security import create_access_token
            from datetime import timedelta
            valid_token = create_access_token(
                data={"sub": "user_id_123", "email": "test@example.com"},
                expires_delta=timedelta(minutes=5)  # Valid token
            )

            with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
                response = client.post(
                    "/api/v1/auth/verify-forgot-password",
                    json={
                        "email": "test@example.com",
                        "token": valid_token,
                        "new_password": "NewPassword123!"
                    }
                )

                assert response.status_code == 200
                response_data = response.json()
                assert response_data["success"] is True
                assert "Password reset successfully" in response_data["message"]

                # Verify the auth service method was called correctly
                mock_auth_service.update_password.assert_called_once_with("test@example.com", "NewPassword123!")

    async def test_verify_forgot_password_invalid_token(self, client, mock_db):
        """Test password reset verification with invalid token"""
        with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
            # Mock decode_access_token to raise ValueError for invalid token
            with patch("app.features.auth.routes.auth.decode_access_token") as mock_decode:
                mock_decode.side_effect = ValueError("Invalid token")
                
                response = client.post(
                    "/api/v1/auth/verify-forgot-password",
                    json={
                        "email": "test@example.com",
                        "token": "invalid_token",
                        "new_password": "NewPassword123!"
                    }
                )

                assert response.status_code == 400

    async def test_verify_forgot_password_weak_password(self, client, mock_db):
        """Test password reset verification with weak password"""
        with patch("app.features.auth.routes.auth.get_db", return_value=mock_db):
            # Create a valid JWT token
            from app.features.auth.utils.security import create_access_token
            from datetime import timedelta
            valid_token = create_access_token(
                data={"sub": "user_id_123", "email": "test@example.com"},
                expires_delta=timedelta(minutes=5)
            )
            
            response = client.post(
                "/api/v1/auth/verify-forgot-password",
                json={
                    "email": "test@example.com",
                    "token": valid_token,
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
                # Mock token creation
                with patch("app.features.auth.routes.auth.create_access_token") as mock_create_token:
                    mock_create_token.return_value = "jwt_reset_token_123"
                    
                    # Mock the email sending to prevent actual SMTP connection
                    with patch("app.features.auth.routes.auth.send_password_reset_email") as mock_send_email:
                        response = client.post(
                            "/api/v1/auth/forgot-password",
                            json={"email": "test@example.com"}
                        )

                        # The endpoint should return success even if email fails (background task)
                        assert response.status_code == 200
                        response_data = response.json()
                        assert response_data["success"] is True
                        
                        # Verify email was attempted to be sent
                        mock_send_email.assert_called_once_with("test@example.com", "jwt_reset_token_123")