"""
WebSocket Authentication

Provides authentication utilities for WebSocket connections.
WebSockets use query parameters for tokens since they don't support custom headers.
"""

from fastapi import WebSocketException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.user import User
from app.features.auth.routes.auth import blacklisted_tokens
from app.features.auth.services.auth_service import AuthService
from app.features.auth.utils.security import decode_access_token
from app.platform.logger import get_logger

logger = get_logger(__name__)


async def authenticate_websocket(token: str, db: AsyncSession) -> User:
    """
    Authenticate a WebSocket connection using a JWT token.

    Args:
        token: JWT access token from query parameter
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        WebSocketException: If authentication fails
    """
    try:
        # Check if token is blacklisted (user logged out)
        if token in blacklisted_tokens:
            logger.warning("WebSocket connection attempted with blacklisted token")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION, reason="Token has been revoked"
            )

        # Decode and validate JWT token
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            logger.warning("WebSocket connection attempted with invalid token payload")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication credentials"
            )

        # Retrieve user from database
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)

        if user is None:
            logger.warning(f"WebSocket connection attempted for non-existent user: {user_id}")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")

        logger.info(f"WebSocket authenticated for user: {user_id}")
        return user

    except ValueError as e:
        # Token decode error
        logger.warning(f"WebSocket authentication failed: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token"
        )
    except WebSocketException:
        # Re-raise WebSocket exceptions
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error during WebSocket authentication: {e}")
        raise WebSocketException(
            code=status.WS_1011_INTERNAL_ERROR, reason="Authentication error"
        )
