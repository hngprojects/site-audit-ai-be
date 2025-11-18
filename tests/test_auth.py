import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.features.auth.models.user import User
from app.platform.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, timedelta

client = TestClient(app)


class TestForgetPassword:
    """Test cases for forget password endpoint"""

    @pytest.mark.asyncio
    async def test_forget_password_success(self, db_session: AsyncSession):
        """Test successful password reset request"""
        # Create a test user
        test_user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            is_email_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(test_user)
        await db_session.commit()

        # Mock the email sending function
        with patch("app.platform.services.email.send_email") as mock_send_email:
            # Make the request
            response = client.post("/auth/forgot-password", json={"email": "test@example.com"})

            # Check response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Password reset email sent" in data["message"]
            assert "1 minute" in data["message"]

            # Check that email was called
            mock_send_email.assert_called_once()

            # Check that reset token was set in database
            await db_session.refresh(test_user)
            assert test_user.password_reset_token is not None
            assert test_user.password_reset_expires_at is not None

            # Check that token expires in 1 minute
            expected_expiry = datetime.utcnow() + timedelta(minutes=1)
            time_diff = abs((test_user.password_reset_expires_at - expected_expiry).total_seconds())
            assert time_diff < 10  # Allow 10 seconds tolerance

    @pytest.mark.asyncio
    async def test_forget_password_user_not_found(self, db_session: AsyncSession):
        """Test password reset request for non-existent user"""
        # Mock the email sending function
        with patch("app.platform.services.email.send_email") as mock_send_email:
            # Make the request
            response = client.post("/auth/forgot-password", json={"email": "nonexistent@example.com"})

            # Check response - should return 404 for non-existent user
            assert response.status_code == 404
            assert "User not found" in str(response.json())

            # Email should not be sent
            mock_send_email.assert_not_called()


class TestResendResetToken:
    """Test cases for resend reset token endpoint"""

    @pytest.mark.asyncio
    async def test_resend_reset_token_success(self, db_session: AsyncSession):
        """Test resending reset token"""
        # Create a test user with existing reset token
        test_user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            is_email_verified=True,
            password_reset_token="old_token",
            password_reset_expires_at=datetime.utcnow() - timedelta(minutes=5),  # Expired
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(test_user)
        await db_session.commit()

        # Mock the email sending function
        with patch("app.platform.services.email.send_email") as mock_send_email:
            # Make the request
            response = client.post("/auth/resend-reset-token", json={"email": "test@example.com"})

            # Check response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "New password reset email sent" in data["message"]
            assert "1 minute" in data["message"]

            # Check that email was called
            mock_send_email.assert_called_once()

            # Check that reset token was updated
            await db_session.refresh(test_user)
            assert test_user.password_reset_token != "old_token"  # Should be different
            assert test_user.password_reset_expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_resend_reset_token_user_not_found(self, db_session: AsyncSession):
        """Test resend reset token for non-existent user"""
        # Mock the email sending function
        with patch("app.platform.services.email.send_email") as mock_send_email:
            # Make the request
            response = client.post("/auth/resend-reset-token", json={"email": "nonexistent@example.com"})

            # Check response
            assert response.status_code == 404
            assert "User not found" in str(response.json())

            # Email should not be sent
            mock_send_email.assert_not_called()


class TestResetPassword:
    """Test cases for reset password endpoint"""

    @pytest.mark.asyncio
    async def test_reset_password_success(self, db_session: AsyncSession):
        """Test successful password reset"""
        # Create a test user with a valid reset token
        reset_token = "valid-reset-token-123"
        test_user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="old_hashed_password",
            is_email_verified=True,
            password_reset_token=reset_token,
            password_reset_expires_at=datetime.utcnow() + timedelta(minutes=5),  # Valid
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(test_user)
        await db_session.commit()

        # Make the request
        response = client.post("/auth/reset-password", json={
            "email": "test@example.com",
            "token": reset_token,
            "new_password": "NewSecurePass123"
        })

        # Check response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Password reset successfully" in data["message"]


        await db_session.refresh(test_user)
        assert test_user.password_reset_token is None
        assert test_user.password_reset_expires_at is None

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, db_session: AsyncSession):
        """Test reset password with invalid token"""
        # Create a test user
        test_user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            is_email_verified=True,
            password_reset_token="valid-token",
            password_reset_expires_at=datetime.utcnow() + timedelta(minutes=5),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(test_user)
        await db_session.commit()

        # Make the request with invalid token
        response = client.post("/auth/reset-password", json={
            "email": "test@example.com",
            "token": "invalid-token-123",
            "new_password": "NewSecurePass123"
        })

        # Check response
        assert response.status_code == 400
        assert "Invalid or expired reset token" in str(response.json())

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self, db_session: AsyncSession):
        """Test reset password with expired token"""
        # Create a test user with expired token
        reset_token = "expired-token-123"
        test_user = User(
            id=str(uuid.uuid4()),
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            is_email_verified=True,
            password_reset_token=reset_token,
            password_reset_expires_at=datetime.utcnow() - timedelta(minutes=5),  # Expired
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(test_user)
        await db_session.commit()

        # Make the request
        response = client.post("/auth/reset-password", json={
            "email": "test@example.com",
            "token": reset_token,
            "new_password": "NewSecurePass123"
        })

        # Check response
        assert response.status_code == 400
        assert "Invalid or expired reset token" in str(response.json())

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self, db_session: AsyncSession):
        """Test reset password for non-existent user"""
        # Make the request
        response = client.post("/auth/reset-password", json={
            "email": "nonexistent@example.com",
            "token": "some-token",
            "new_password": "NewSecurePass123"
        })

        # Check response
        assert response.status_code == 404
        assert "User not found" in str(response.json())

    def test_reset_password_weak_password(self):
        """Test reset password with weak password (validation error)"""
        # This should fail at Pydantic validation level
        response = client.post("/auth/reset-password", json={
            "email": "test@example.com",
            "token": "some-token",
            "new_password": "weak"
        })

        # Should fail password validation
        assert response.status_code == 422  # Validation error