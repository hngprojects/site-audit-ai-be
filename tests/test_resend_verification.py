import pytest
import uuid
from uuid6 import uuid7
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.main import app

pytestmark = pytest.mark.skip(reason="Resend verification endpoint is not implemented in the current API")

client = TestClient(app)


class TestResendVerification:
    """Test suite for POST /auth/resend-verification endpoint"""

    @pytest.fixture
    def unique_user_data(self):
        """Generate unique user data for each test"""
        unique_id = str(uuid.uuid4())[:8]
        return {
            "email": f"testuser{unique_id}@example.com",
            "username": f"testuser{unique_id}",
            "password": "TestPassword123"
        }

    @pytest.fixture
    def create_unverified_user(self, unique_user_data):
        """Create an unverified user for testing"""
        with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send:
            mock_send.return_value = None
            response = client.post("/api/v1/auth/signup", json=unique_user_data)
            assert response.status_code == 201
            return unique_user_data["email"]

    def test_resend_verification_success(self, create_unverified_user):
        """Test successful resend of verification code"""
        email = create_unverified_user

        with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send:
            mock_send.return_value = None

            response = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )

            # Assert response structure
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
            data = response.json()

            # Check response contains expected fields
            assert "success" in data
            assert data["success"] is True
            assert "message" in data
            assert "resent" in data["message"].lower() or "sent" in data["message"].lower()
            assert "data" in data
            assert data["data"]["email"] == email

            # Verify email sending was called
            mock_send.assert_called_once()

    def test_resend_verification_email_not_found(self):
        """Test resend with non-existent email returns 404"""
        response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "nonexistent@example.com"}
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_resend_verification_already_verified(self, create_unverified_user):
        """Test resend for already verified user returns 400"""
        email = create_unverified_user

        # First, manually verify the user in the database
        # This requires accessing the database directly
        from app.platform.db.session import SessionLocal
        from app.features.auth.models.user import User
        from sqlalchemy import select
        import asyncio

        async def verify_user():
            async with SessionLocal() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    user.is_email_verified = True
                    user.email_verified_at = datetime.utcnow()
                    await db.commit()

        # Run the async function
        asyncio.run(verify_user())

        # Now try to resend verification
        response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": email}
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "already verified" in data["detail"].lower()

    def test_resend_verification_rate_limit_cooldown(self, create_unverified_user):
        """Test rate limiting - cooldown period (60 seconds)"""
        email = create_unverified_user

        with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send:
            mock_send.return_value = None

            # First resend - should succeed
            response1 = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            assert response1.status_code == 200

            # Immediate second resend - should fail with 429
            response2 = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            assert response2.status_code == 429
            data = response2.json()
            assert "detail" in data
            assert "wait" in data["detail"].lower() or "too many" in data["detail"].lower()

    def test_resend_verification_rate_limit_hourly_max(self, create_unverified_user):
        """Test rate limiting - maximum 3 attempts per hour"""
        email = create_unverified_user

        # We need to mock the time checks to simulate rapid attempts
        # This test simulates waiting 60 seconds between each attempt
        from app.features.auth.models.user import User
        from app.platform.db.session import SessionLocal
        from sqlalchemy import select
        import asyncio

        async def reset_last_resent_time():
            """Helper to reset the last resent time to allow immediate retry"""
            async with SessionLocal() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    # Set last resent time to 61 seconds ago
                    user.otp_last_resent_at = datetime.utcnow() - timedelta(seconds=61)
                    await db.commit()

        with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send:
            mock_send.return_value = None

            # Attempt 1 - should succeed
            response1 = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            assert response1.status_code == 200

            # Reset cooldown
            asyncio.run(reset_last_resent_time())

            # Attempt 2 - should succeed
            response2 = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            assert response2.status_code == 200

            # Reset cooldown
            asyncio.run(reset_last_resent_time())

            # Attempt 3 - should succeed
            response3 = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            assert response3.status_code == 200

            # Reset cooldown
            asyncio.run(reset_last_resent_time())

            # Attempt 4 - should fail with 429 (hourly limit exceeded)
            response4 = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            assert response4.status_code == 429
            data = response4.json()
            assert "detail" in data
            assert "maximum" in data["detail"].lower() or "exceeded" in data["detail"].lower()

    def test_resend_verification_invalid_email_format(self):
        """Test resend with invalid email format returns 422"""
        response = client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "not-an-email"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_resend_verification_missing_email(self):
        """Test resend without email field returns 422"""
        response = client.post(
            "/api/v1/auth/resend-verification",
            json={}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_resend_verification_case_insensitive_email(self, create_unverified_user):
        """Test resend works with different email casing"""
        email = create_unverified_user
        email_upper = email.upper()

        with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send:
            mock_send.return_value = None

            response = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email_upper}
            )

            # Should succeed - email lookup is case-insensitive
            assert response.status_code == 200
            mock_send.assert_called_once()

    def test_resend_verification_generates_new_otp(self, create_unverified_user):
        """Test that resend generates a new OTP (not reusing old one)"""
        email = create_unverified_user

        # Get the initial OTP from database
        from app.platform.db.session import SessionLocal
        from app.features.auth.models.user import User
        from sqlalchemy import select
        import asyncio

        async def get_otp():
            async with SessionLocal() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                return user.verification_otp if user else None

        initial_otp = asyncio.run(get_otp())

        # Wait to bypass cooldown
        async def reset_cooldown():
            async with SessionLocal() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    user.otp_last_resent_at = datetime.utcnow() - timedelta(seconds=61)
                    await db.commit()

        asyncio.run(reset_cooldown())

        # Resend verification
        with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send:
            mock_send.return_value = None

            response = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            assert response.status_code == 200

        # Get new OTP
        new_otp = asyncio.run(get_otp())

        # OTPs should be different (new one generated)
        assert initial_otp != new_otp
        assert new_otp is not None
        assert len(new_otp) == 6  # 6-digit OTP

    def test_resend_verification_updates_expiry(self, create_unverified_user):
        """Test that resend updates the OTP expiry timestamp"""
        email = create_unverified_user

        from app.platform.db.session import SessionLocal
        from app.features.auth.models.user import User
        from sqlalchemy import select
        import asyncio

        async def get_expiry():
            async with SessionLocal() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                return user.otp_expires_at if user else None

        initial_expiry = asyncio.run(get_expiry())

        # Wait to bypass cooldown
        async def reset_cooldown():
            async with SessionLocal() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    user.otp_last_resent_at = datetime.utcnow() - timedelta(seconds=61)
                    await db.commit()

        asyncio.run(reset_cooldown())
        time.sleep(1)  # Ensure timestamp difference

        # Resend verification
        with patch("app.features.auth.routes.auth.send_verification_otp") as mock_send:
            mock_send.return_value = None

            response = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": email}
            )
            assert response.status_code == 200

        new_expiry = asyncio.run(get_expiry())

        # Expiry should be updated (different timestamp)
        assert new_expiry > initial_expiry

        # New expiry should be approximately 10 minutes from now
        time_diff = (new_expiry - datetime.utcnow()).total_seconds()
        assert 595 < time_diff < 605  # Within 5 seconds of 10 minutes

# Run tests with: pytest tests/test_resend_verification.py -v
# Run specific test: pytest tests/test_resend_verification.py::TestResendVerification::test_resend_verification_success -v
# Run with coverage: pytest tests/test_resend_verification.py --cov=app.features.auth --cov-report=html
