import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from fastapi import HTTPException, status
import redis
import os

from ..models import ErrorCode

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY", "your-refresh-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

# Setup logging
logger = logging.getLogger(__name__)

# Redis client for token blacklist
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)


class AuthService:

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Access token created for user: {data.get('sub')}")
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Refresh token created for user: {data.get('sub')}")
        return encoded_jwt

    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        try:
            return redis_client.exists(f"blacklist:{token}") > 0
        except Exception as e:
            logger.error(f"Redis error checking blacklist: {str(e)}")
            return False

    @staticmethod
    def blacklist_token(token: str, expire_time: int):
        try:
            redis_client.setex(
                f"blacklist:{token}",
                expire_time,
                "revoked"
            )
            logger.info(f"Token added to blacklist with TTL: {expire_time}s")
        except Exception as e:
            logger.error(f"Redis error adding to blacklist: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to invalidate token"
            )

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        if AuthService.is_token_blacklisted(token):
            logger.warning(f"Attempt to use blacklisted token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Token has been revoked",
                    "error_code": ErrorCode.TOKEN_INVALID,
                    "message": "This token has been invalidated. Please log in again."
                }
            )
        
        try:
            # Decode token
            secret = SECRET_KEY if token_type == "access" else REFRESH_SECRET_KEY
            payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
            
            # Verify token type
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "error": "Invalid token type",
                        "error_code": ErrorCode.TOKEN_INVALID,
                        "message": f"Expected {token_type} token"
                    }
                )
            
            return payload
            
        except ExpiredSignatureError:
            logger.info(f"Session timeout - Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Token expired",
                    "error_code": ErrorCode.TOKEN_EXPIRED,
                    "message": "Your session has expired due to inactivity. Please log in again.",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        except InvalidTokenError as e:
            logger.warning(f"Invalid token attempt: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Invalid token",
                    "error_code": ErrorCode.TOKEN_INVALID,
                    "message": "The provided token is invalid. Please log in again."
                }
            )
