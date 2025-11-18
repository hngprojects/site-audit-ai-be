from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.users import User
from app.features.auth.services.user_service import UserService, generate_username_from_email
from app.platform.config import settings


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


class TestGenerateUsername:
    """Test suite for username generation"""

    @pytest.mark.asyncio
    async def test_generate_username_basic(self, db_session: AsyncSession):
        """Test basic username generation from email"""
        with patch.object(db_session, "execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_execute.return_value = mock_result

            username = await generate_username_from_email("john.doe@example.com", db_session)

            assert username == "john_doe"

    @pytest.mark.asyncio
    async def test_generate_username_with_special_chars(self, db_session: AsyncSession):
        """Test username generation with special characters"""
        with patch.object(db_session, "execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_execute.return_value = mock_result

            username = await generate_username_from_email("user+test@example.com", db_session)

            assert username == "user_test"

    @pytest.mark.asyncio
    async def test_generate_username_collision_handling(self, db_session: AsyncSession):
        """Test username generation when username already exists"""
        with patch.object(db_session, "execute") as mock_execute:
            # First call: username exists
            # Second call: username1 is available
            mock_result_exists = MagicMock()
            mock_result_exists.scalar_one_or_none.return_value = User(username="testuser")

            mock_result_available = MagicMock()
            mock_result_available.scalar_one_or_none.return_value = None

            mock_execute.side_effect = [mock_result_exists, mock_result_available]

            username = await generate_username_from_email("testuser@example.com", db_session)

            assert username == "testuser1"

    @pytest.mark.asyncio
    async def test_generate_username_multiple_collisions(self, db_session: AsyncSession):
        """Test username generation with multiple collisions"""
        with patch.object(db_session, "execute") as mock_execute:
            # Simulate multiple collisions
            mock_result_exists = MagicMock()
            mock_result_exists.scalar_one_or_none.return_value = User(username="testuser")

            mock_result_available = MagicMock()
            mock_result_available.scalar_one_or_none.return_value = None

            mock_execute.side_effect = [
                mock_result_exists,  # testuser exists
                mock_result_exists,  # testuser1 exists
                mock_result_exists,  # testuser2 exists
                mock_result_available,  # testuser3 available
            ]

            username = await generate_username_from_email("testuser@example.com", db_session)

            assert username == "testuser3"


class TestUserService:
    """Test suite for UserService"""

    def test_create_access_token_default_expiration(self):
        """Test creating access token with default expiration"""
        user_data = {"sub": str(uuid4()), "email": "test@example.com"}

        token = UserService.create_access_token(user_data)

        # Decode and verify token
        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert decoded["sub"] == user_data["sub"]
        assert decoded["email"] == user_data["email"]
        assert "exp" in decoded

    def test_create_access_token_custom_expiration(self):
        """Test creating access token with custom expiration"""
        user_data = {"sub": str(uuid4()), "email": "test@example.com"}
        expires_delta = timedelta(days=7)

        token = UserService.create_access_token(user_data, expires_delta)

        decoded = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Verify expiration is approximately 7 days from now
        exp_timestamp = decoded["exp"]
        exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
        expected_exp = datetime.utcnow() + expires_delta

        # Allow 5 second tolerance
        assert abs((exp_datetime - expected_exp).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, db_session: AsyncSession):
        """Test successful user retrieval from valid token"""
        user_id = uuid4()
        user = User(id=user_id, email="test@example.com", username="testuser", user_confirmed=True)

        # Create a valid token
        token_data = {"sub": str(user_id), "email": "test@example.com"}
        token = UserService.create_access_token(token_data)

        # Mock credentials
        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        # Mock database query
        with patch.object(db_session, "execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = user
            mock_execute.return_value = mock_result

            result = await UserService.get_current_user(mock_credentials, db_session)

            assert result.id == user_id
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db_session: AsyncSession):
        """Test user retrieval with invalid token"""
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid_token"

        with pytest.raises(HTTPException) as exc_info:
            await UserService.get_current_user(mock_credentials, db_session)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub(self, db_session: AsyncSession):
        """Test user retrieval when token is missing 'sub' claim"""
        # Create token without 'sub'
        token_data = {"email": "test@example.com"}
        token = jwt.encode(
            {**token_data, "exp": datetime.utcnow() + timedelta(minutes=30)},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await UserService.get_current_user(mock_credentials, db_session)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found(self, db_session: AsyncSession):
        """Test user retrieval when user doesn't exist in database"""
        user_id = uuid4()
        token_data = {"sub": str(user_id), "email": "test@example.com"}
        token = UserService.create_access_token(token_data)

        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        # Mock database query returning None
        with patch.object(db_session, "execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_execute.return_value = mock_result

            with pytest.raises(HTTPException) as exc_info:
                await UserService.get_current_user(mock_credentials, db_session)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, db_session: AsyncSession):
        """Test user retrieval with expired token"""
        user_id = uuid4()
        token_data = {"sub": str(user_id), "email": "test@example.com"}

        # Create expired token
        token = UserService.create_access_token(token_data, expires_delta=timedelta(seconds=-1))

        mock_credentials = MagicMock()
        mock_credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            await UserService.get_current_user(mock_credentials, db_session)

        assert exc_info.value.status_code == 401
