from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.oauth import OAuthAccount
from app.features.auth.models.users import User
from app.features.auth.services.oauth_service import OAuthService


@pytest.fixture
def db_session():
    """Mock database session fixture"""
    session = MagicMock(spec=AsyncSession)
    return session


@pytest.fixture
def client():
    """Test client fixture"""
    from app.main import app

    return TestClient(app)


class TestOAuthService:
    """Test suite for OAuthService"""

    @pytest.mark.asyncio
    async def test_verify_google_token_success(self):
        """Test successful Google token verification"""
        mock_token = "valid_token"
        mock_payload = {
            "iss": "accounts.google.com",
            "sub": "123456789",
            "email": "test@example.com",
            "email_verified": True,
            "given_name": "John",
            "family_name": "Doe",
        }

        with patch(
            "app.features.auth.services.oauth_service.id_token.verify_oauth2_token"
        ) as mock_verify:
            mock_verify.return_value = mock_payload

            result = await OAuthService.verify_google_token(mock_token)

            assert result == mock_payload
            mock_verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_google_token_wrong_issuer(self):
        """Test Google token verification with wrong issuer"""
        mock_token = "invalid_token"
        mock_payload = {"iss": "wrong.issuer.com", "sub": "123456789", "email": "test@example.com"}

        with patch(
            "app.features.auth.services.oauth_service.id_token.verify_oauth2_token"
        ) as mock_verify:
            mock_verify.return_value = mock_payload

            with pytest.raises(ValueError, match="Wrong issuer"):
                await OAuthService.verify_google_token(mock_token)

    @pytest.mark.asyncio
    async def test_verify_google_token_invalid_token(self):
        """Test Google token verification with invalid token"""
        mock_token = "invalid_token"

        with patch(
            "app.features.auth.services.oauth_service.id_token.verify_oauth2_token"
        ) as mock_verify:
            mock_verify.side_effect = Exception("Token validation failed")

            with pytest.raises(ValueError, match="Invalid token"):
                await OAuthService.verify_google_token(mock_token)

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_oauth_account(self, db_session: AsyncSession):
        """Test retrieving user with existing OAuth account"""
        # Setup
        user_id = uuid4()
        existing_user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
            first_name="John",
            last_name="Doe",
            user_confirmed=True,
        )

        existing_oauth = OAuthAccount(
            id=uuid4(),
            user_id=user_id,
            provider="google",
            provider_user_id="123456789",
            profile_data={"sub": "123456789"},
        )

        google_user_info = {
            "sub": "123456789",
            "email": "test@example.com",
            "given_name": "John",
            "family_name": "Doe",
            "email_verified": True,
        }

        # Mock database queries
        with patch.object(db_session, "execute") as mock_execute:
            # First query: find OAuth account
            mock_result_oauth = MagicMock()
            mock_result_oauth.scalars().first.return_value = existing_oauth

            # Second query: find user
            mock_result_user = MagicMock()
            mock_result_user.scalar_one.return_value = existing_user

            mock_execute.side_effect = [mock_result_oauth, mock_result_user]

            with patch.object(db_session, "commit", new_callable=AsyncMock):
                with patch.object(db_session, "refresh", new_callable=AsyncMock):
                    result = await OAuthService.get_or_create_user_from_google(
                        db_session, google_user_info
                    )

            assert result.id == user_id
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_user_new_oauth(self, db_session: AsyncSession):
        """Test linking OAuth to existing user without OAuth account"""
        user_id = uuid4()
        existing_user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
            first_name="John",
            last_name="Doe",
            user_confirmed=True,
        )

        google_user_info = {
            "sub": "123456789",
            "email": "test@example.com",
            "given_name": "John",
            "family_name": "Doe",
            "email_verified": True,
        }

        with patch.object(db_session, "execute") as mock_execute:
            # First query: no OAuth account
            mock_result_oauth = MagicMock()
            mock_result_oauth.scalars().first.return_value = None

            # Second query: find existing user by email
            mock_result_user = MagicMock()
            mock_result_user.scalar_one_or_none.return_value = existing_user

            mock_execute.side_effect = [mock_result_oauth, mock_result_user]

            with patch.object(db_session, "add") as mock_add:
                with patch.object(db_session, "commit", new_callable=AsyncMock):
                    with patch.object(db_session, "refresh", new_callable=AsyncMock):
                        result = await OAuthService.get_or_create_user_from_google(
                            db_session, google_user_info
                        )

            assert result.id == user_id
            # Verify OAuth account was created
            assert mock_add.call_count == 1

    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user(self, db_session: AsyncSession):
        """Test creating new user with OAuth account"""
        google_user_info = {
            "sub": "123456789",
            "email": "newuser@example.com",
            "given_name": "Jane",
            "family_name": "Smith",
            "email_verified": True,
        }

        with patch.object(db_session, "execute") as mock_execute:
            # First query: no OAuth account
            mock_result_oauth = MagicMock()
            mock_result_oauth.scalars().first.return_value = None

            # Second query: no existing user
            mock_result_user = MagicMock()
            mock_result_user.scalar_one_or_none.return_value = None

            mock_execute.side_effect = [mock_result_oauth, mock_result_user]

            created_user = User(
                id=uuid4(),
                email="newuser@example.com",
                username="newuser",
                first_name="Jane",
                last_name="Smith",
                user_confirmed=True,
                password=None,
            )

            with patch.object(db_session, "add") as mock_add:
                with patch.object(db_session, "flush", new_callable=AsyncMock):
                    with patch.object(db_session, "commit", new_callable=AsyncMock):
                        with patch.object(
                            db_session, "refresh", new_callable=AsyncMock
                        ) as mock_refresh:
                            with patch(
                                "app.features.auth.services.oauth_service.generate_username_from_email",
                                return_value="newuser",
                            ):
                                # Set the user after add is called
                                def side_effect(obj):
                                    if isinstance(obj, User):
                                        obj.id = created_user.id

                                mock_add.side_effect = side_effect
                                mock_refresh.side_effect = lambda obj: None

                                await OAuthService.get_or_create_user_from_google(
                                    db_session, google_user_info
                                )

            # Verify user and OAuth account were created
            assert mock_add.call_count == 2  # User + OAuthAccount

    @pytest.mark.asyncio
    async def test_get_or_create_user_missing_required_fields(self, db_session: AsyncSession):
        """Test error handling when required fields are missing"""
        # Missing sub
        google_user_info = {"email": "test@example.com"}

        with pytest.raises(ValueError, match="Invalid Google user info"):
            await OAuthService.get_or_create_user_from_google(db_session, google_user_info)

        # Missing email
        google_user_info = {"sub": "123456789"}

        with pytest.raises(ValueError, match="Invalid Google user info"):
            await OAuthService.get_or_create_user_from_google(db_session, google_user_info)
