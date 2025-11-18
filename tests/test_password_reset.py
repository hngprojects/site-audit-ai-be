"""
Test cases for password reset functionality.

Run with: pytest tests/test_password_reset.py -v
"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.features.auth.models.user import User
from app.features.auth.utils.password import hash_password
from app.platform.db.session import get_db, SessionLocal


class TestPasswordReset:
    """Test suite for password reset endpoints."""
    
    @pytest.mark.asyncio
    async def test_request_password_reset_success(self, client: AsyncClient, test_user: User):
        """Test successful password reset request."""
        response = await client.post(
            "/auth/request-password-reset",
            json={"email": test_user.email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "reset link" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_email(self, client: AsyncClient):
        """Test password reset request with non-existent email."""
        response = await client.post(
            "/auth/request-password-reset",
            json={"email": "zinsusezonsu@gmail.com"}
        )
        
        # Should return 200 for security (don't reveal if email exists)
        assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_request_password_reset_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/auth/request-password-reset",
            json={"email": "invalid-email"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_reset_password_success(
        self, client: AsyncClient, test_user_with_token: User, valid_token: str
    ):
        """Test successful password reset."""
        new_password = "NewSecurePassword123!"
        
        response = await client.post(
            "/auth/reset-password",
            json={
                "token": valid_token,
                "new_password": new_password
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, client: AsyncClient):
        """Test password reset with invalid token."""
        response = await client.post(
            "/auth/reset-password",
            json={
                "token": "invalid_token_12345",
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "invalid" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_reset_password_expired_token(
        self, client: AsyncClient, test_user_with_expired_token: User, expired_token: str
    ):
        """Test password reset with expired token."""
        response = await client.post(
            "/auth/reset-password",
            json={
                "token": expired_token,
                "new_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "expired" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_reset_password_short_password(self, client: AsyncClient, valid_token: str):
        """Test password reset with password too short."""
        response = await client.post(
            "/auth/reset-password",
            json={
                "token": valid_token,
                "new_password": "short"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_token_cleared_after_reset(
        self, client: AsyncClient, db: AsyncSession, test_user_with_token: User, valid_token: str
    ):
        """Test that reset token is cleared after successful password reset."""
        # Reset password
        await client.post(
            "/auth/reset-password",
            json={
                "token": valid_token,
                "new_password": "NewPassword123!"
            }
        )
        
        # Refresh user from database
        await db.refresh(test_user_with_token)
        
        # Token should be cleared
        assert test_user_with_token.reset_token is None
        assert test_user_with_token.reset_token_expiry is None


# Fixtures for testing

@pytest.fixture
async def client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db():
    """Create a database session for testing."""
    async with SessionLocal() as session:
        yield session


@pytest.fixture
async def test_user(db: AsyncSession):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password=hash_password("TestPassword123!")
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    yield user
    
    # Cleanup
    await db.delete(user)
    await db.commit()


@pytest.fixture
async def valid_token() -> str:
    """Generate a valid reset token."""
    import secrets
    return secrets.token_urlsafe(48)


@pytest.fixture
async def test_user_with_token(db: AsyncSession, valid_token: str):
    """Create a test user with a valid reset token."""
    user = User(
        email="test_token@example.com",
        password=hash_password("TestPassword123!"),
        reset_token=valid_token,
        reset_token_expiry=datetime.utcnow() + timedelta(minutes=30)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    yield user
    
    # Cleanup
    await db.delete(user)
    await db.commit()


@pytest.fixture
async def expired_token() -> str:
    """Generate an expired reset token."""
    import secrets
    return secrets.token_urlsafe(48)


@pytest.fixture
async def test_user_with_expired_token(db: AsyncSession, expired_token: str):
    """Create a test user with an expired reset token."""
    user = User(
        email="test_expired@example.com",
        password=hash_password("TestPassword123!"),
        reset_token=expired_token,
        reset_token_expiry=datetime.utcnow() - timedelta(minutes=1)  # Expired
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    yield user
    
    # Cleanup
    await db.delete(user)
    await db.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
