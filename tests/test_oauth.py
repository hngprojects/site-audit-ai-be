from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.oauth import OAuthAccount
from app.features.auth.models.user import User
from app.features.auth.schemas.auth import GoogleAuthRequest
from app.main import app

client = TestClient(app)


class TestOAuthRoutes:
    """Test OAuth authentication routes"""

    @pytest.mark.asyncio
    @patch("app.features.auth.services.oauth_service.GoogleOAuthVerifier.verify_token")
    @patch("app.features.auth.services.oauth_service.generate_unique_username")
    async def test_google_auth_new_user(
        self, mock_generate_username, mock_verify_token, async_session
    ):
        """Test Google OAuth authentication for new user"""
        # Mock Google token verification
        mock_verify_token.return_value = {
            "provider_user_id": "123456789",
            "email": "test@example.com",
            "email_verified": True,
            "given_name": "John",
            "family_name": "Doe",
            "name": "John Doe",
        }

        # Mock username generation
        mock_generate_username.return_value = "johndoe"

        # Mock database operations
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        def mock_refresh(obj):
            if hasattr(obj, "created_at") and obj.created_at is None:
                obj.created_at = datetime.utcnow()
            if hasattr(obj, "updated_at") and obj.updated_at is None:
                obj.updated_at = datetime.utcnow()

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)

        # Create request
        request = GoogleAuthRequest(id_token="fake_google_token", platform="ios")

        # Import and test the service directly
        from app.features.auth.services.oauth_service import OAuthService

        oauth_service = OAuthService(mock_db)

        result = await oauth_service.authenticate_with_google(request)

        # Verify the result
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.token_type == "bearer"
        assert result.user.email == "test@example.com"
        assert result.user.first_name == "John"
        assert result.user.last_name == "Doe"
        assert result.user.is_email_verified is True

        # Verify database operations
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    @patch("app.features.auth.services.oauth_service.GoogleOAuthVerifier.verify_token")
    async def test_google_auth_existing_oauth_user(self, mock_verify_token, async_session):
        """Test Google OAuth authentication for existing OAuth user"""
        # Mock Google token verification
        mock_verify_token.return_value = {
            "provider_user_id": "123456789",
            "email": "test@example.com",
            "email_verified": True,
            "given_name": "John",
            "family_name": "Doe",
        }

        # Mock existing OAuth account and user
        mock_user = User(
            id="user-123",
            email="test@example.com",
            username="johndoe",
            first_name="John",
            last_name="Doe",
            is_email_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_oauth_account = OAuthAccount(
            user_id="user-123",
            provider="google",
            provider_user_id="123456789",
            provider_email="test@example.com",
        )

        # Mock database operations
        mock_db = AsyncMock(spec=AsyncSession)

        # First call returns OAuth account, second call returns user
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_oauth_account
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_user
        mock_db.execute.side_effect = [mock_result1, mock_result2]

        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Create request
        request = GoogleAuthRequest(id_token="fake_google_token", platform="ios")

        # Test the service
        from app.features.auth.services.oauth_service import OAuthService

        oauth_service = OAuthService(mock_db)

        result = await oauth_service.authenticate_with_google(request)

        # Verify the result
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.user.email == "test@example.com"

        # Verify database operations
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called()

    @pytest.mark.asyncio
    @patch("app.features.auth.services.oauth_service.GoogleOAuthVerifier.verify_token")
    @patch("app.features.auth.services.oauth_service.generate_unique_username")
    async def test_google_auth_existing_email_user(
        self, mock_generate_username, mock_verify_token, async_session
    ):
        """Test Google OAuth authentication for existing user with same email but no OAuth"""
        # Mock Google token verification
        mock_verify_token.return_value = {
            "provider_user_id": "123456789",
            "email": "test@example.com",
            "email_verified": True,
            "given_name": "John",
            "family_name": "Doe",
        }

        # Mock existing user (no OAuth account yet)
        mock_user = User(
            id="user-123",
            email="test@example.com",
            username="existinguser",
            is_email_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Mock database operations
        mock_db = AsyncMock(spec=AsyncSession)

        # First call returns None (no OAuth account), second call returns existing user
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = None
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_user
        mock_db.execute.side_effect = [mock_result1, mock_result2]

        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Create request
        request = GoogleAuthRequest(id_token="fake_google_token", platform="ios")

        # Test the service
        from app.features.auth.services.oauth_service import OAuthService

        oauth_service = OAuthService(mock_db)

        result = await oauth_service.authenticate_with_google(request)

        # Verify the result
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.user.email == "test@example.com"

        # Verify OAuth account was created
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

        # Verify user's email verification status was updated
        assert mock_user.is_email_verified is True

    @pytest.mark.asyncio
    @patch("app.features.auth.services.oauth_service.GoogleOAuthVerifier.verify_token")
    async def test_google_auth_invalid_token(self, mock_verify_token, async_session):
        """Test Google OAuth authentication with invalid token"""
        # Mock token verification failure
        from fastapi import HTTPException

        mock_verify_token.side_effect = HTTPException(
            status_code=401, detail="Invalid Google token"
        )

        # Mock database
        mock_db = AsyncMock(spec=AsyncSession)

        # Create request
        request = GoogleAuthRequest(id_token="invalid_token", platform="ios")

        # Test the service
        from app.features.auth.services.oauth_service import OAuthService

        oauth_service = OAuthService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            await oauth_service.authenticate_with_google(request)

        assert exc_info.value.status_code == 401
        assert "Invalid Google token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.features.auth.services.oauth_service.GoogleOAuthVerifier.verify_token")
    @patch("app.features.auth.services.oauth_service.generate_unique_username")
    async def test_google_auth_database_error(
        self, mock_generate_username, mock_verify_token, async_session
    ):
        """Test Google OAuth authentication with database error"""
        # Mock Google token verification
        mock_verify_token.return_value = {
            "provider_user_id": "123456789",
            "email": "test@example.com",
            "email_verified": True,
            "given_name": "John",
            "family_name": "Doe",
        }

        # Mock username generation
        mock_generate_username.return_value = "johndoe"

        # Mock database operations with error
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.flush = AsyncMock()

        # Mock database commit error
        from sqlalchemy.exc import IntegrityError

        mock_db.commit.side_effect = IntegrityError("statement", "params", "orig")
        mock_db.rollback = AsyncMock()

        # Create request
        request = GoogleAuthRequest(id_token="fake_google_token", platform="ios")

        # Test the service
        from app.features.auth.services.oauth_service import OAuthService

        oauth_service = OAuthService(mock_db)

        with pytest.raises(HTTPException) as exc_info:
            await oauth_service.authenticate_with_google(request)

        assert exc_info.value.status_code == 400
        assert "Failed to create user account" in str(exc_info.value.detail)

        # Verify rollback was called
        mock_db.rollback.assert_called_once()

    def test_google_auth_endpoint_invalid_request(self):
        """Test Google OAuth endpoint with invalid request"""
        # Test with missing id_token
        response = client.post("/api/v1/auth/oauth/google", json={"platform": "ios"})
        assert response.status_code == 422  # Validation error

    def test_google_auth_endpoint_invalid_platform(self):
        """Test Google OAuth endpoint with invalid platform"""
        client.post(
            "/api/v1/auth/oauth/google",
            json={"id_token": "some_token", "platform": "invalid_platform"},
        )
        # Should still work as platform is optional and defaults to ios
        # The validation happens in the OAuth verifier, not in the request schema


class TestGoogleOAuthVerifier:
    """Test Google OAuth token verification"""

    @patch("app.features.auth.utils.oauth.GOOGLE_CLIENT_ID", "test_client_id")
    @patch("app.features.auth.utils.oauth.GOOGLE_CLIENT_ID_ANDROID", "test_android_client_id")
    @patch("app.features.auth.utils.oauth.id_token.verify_oauth2_token")
    def test_verify_token_ios_success(self, mock_verify):
        """Test successful token verification for iOS"""
        mock_verify.return_value = {
            "sub": "123456789",
            "email": "test@example.com",
            "email_verified": True,
            "iss": "accounts.google.com",
        }

        from app.features.auth.utils.oauth import GoogleOAuthVerifier

        result = GoogleOAuthVerifier.verify_token("fake_token", "ios")

        assert result["provider_user_id"] == "123456789"
        assert result["email"] == "test@example.com"
        assert result["email_verified"] is True
        mock_verify.assert_called_once()

    @patch("app.features.auth.utils.oauth.GOOGLE_CLIENT_ID", "test_client_id")
    @patch("app.features.auth.utils.oauth.GOOGLE_CLIENT_ID_ANDROID", "test_android_client_id")
    @patch("app.features.auth.utils.oauth.id_token.verify_oauth2_token")
    def test_verify_token_android_success(self, mock_verify):
        """Test successful token verification for Android"""
        mock_verify.return_value = {
            "sub": "123456789",
            "email": "test@example.com",
            "email_verified": True,
            "iss": "https://accounts.google.com",
        }

        from app.features.auth.utils.oauth import GoogleOAuthVerifier

        result = GoogleOAuthVerifier.verify_token("fake_token", "android")

        assert result["provider_user_id"] == "123456789"
        assert result["email"] == "test@example.com"
        assert result["email_verified"] is True

    @patch("app.features.auth.utils.oauth.GOOGLE_CLIENT_ID", None)
    def test_verify_token_no_client_id(self):
        """Test token verification with no client ID configured"""
        from app.features.auth.utils.oauth import GoogleOAuthVerifier

        with pytest.raises(Exception) as exc_info:
            GoogleOAuthVerifier.verify_token("fake_token", "ios")

        assert "Google OAuth not configured" in str(exc_info.value.detail)

    @patch("app.features.auth.utils.oauth.GOOGLE_CLIENT_ID", "test_client_id")
    @patch("app.features.auth.utils.oauth.id_token.verify_oauth2_token")
    def test_verify_token_invalid_issuer(self, mock_verify):
        """Test token verification with invalid issuer"""
        mock_verify.return_value = {
            "sub": "123456789",
            "email": "test@example.com",
            "iss": "invalid-issuer.com",
        }

        from app.features.auth.utils.oauth import GoogleOAuthVerifier

        with pytest.raises(Exception) as exc_info:
            GoogleOAuthVerifier.verify_token("fake_token", "ios")

        assert "Invalid Google token" in str(exc_info.value.detail)

    @patch("app.features.auth.utils.oauth.GOOGLE_CLIENT_ID", "test_client_id")
    @patch("app.features.auth.utils.oauth.id_token.verify_oauth2_token")
    def test_verify_token_verification_error(self, mock_verify):
        """Test token verification with verification error"""
        mock_verify.side_effect = ValueError("Invalid token")

        from app.features.auth.utils.oauth import GoogleOAuthVerifier

        with pytest.raises(Exception) as exc_info:
            GoogleOAuthVerifier.verify_token("fake_token", "ios")

        assert "Invalid Google token" in str(exc_info.value.detail)


class TestOAuthModels:
    """Test OAuth model functionality"""

    def test_oauth_account_creation(self):
        """Test OAuth account model creation"""
        oauth_account = OAuthAccount(
            user_id="user-123",
            provider="google",
            provider_user_id="123456789",
            provider_email="test@example.com",
            provider_data={"name": "John Doe"},
        )

        assert oauth_account.user_id == "user-123"
        assert oauth_account.provider == "google"
        assert oauth_account.provider_user_id == "123456789"
        assert oauth_account.provider_email == "test@example.com"
        assert oauth_account.provider_data["name"] == "John Doe"

    def test_oauth_account_repr(self):
        """Test OAuth account string representation"""
        oauth_account = OAuthAccount(
            user_id="user-123", provider="google", provider_user_id="123456789"
        )

        repr_str = repr(oauth_account)
        assert "user-123" in repr_str
        assert "google" in repr_str


@pytest.fixture
def async_session():
    """Mock async session fixture"""
    return AsyncMock(spec=AsyncSession)
