from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime
import logging
import jwt

from ..models import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    User,
    LogoutResponse,
    ErrorCode
)
from ..services import AuthService

logger = logging.getLogger(__name__)

security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    if not credentials:
        logger.warning(f"Request without token to {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "No authentication token provided",
                "error_code": ErrorCode.TOKEN_MISSING,
                "message": "Authentication required"
            }
        )
    
    token = credentials.credentials
    
    payload = AuthService.verify_token(token, token_type="access")
    
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Invalid token payload",
                "error_code": ErrorCode.TOKEN_INVALID,
                "message": "Token does not contain valid user information"
            }
        )
    
    return User(
        user_id=user_id,
        email=email,
        full_name=payload.get("full_name", "")
    )


@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    user_data = AuthService.authenticate_user(login_data.email, login_data.password)
    
    if not user_data:
        logger.warning(f"Failed login attempt for email: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    token_data = {
        "sub": user_data["user_id"],
        "email": user_data["email"],
        "full_name": user_data["full_name"]
    }
    
    access_token = AuthService.create_access_token(token_data)
    refresh_token = AuthService.create_refresh_token(token_data)
    
    logger.info(
        f"User logged in - UserID: {user_data['user_id']}, "
        f"Email: {user_data['email']}, "
        f"Timestamp: {datetime.utcnow().isoformat()}"
    )
    
    from ..services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(refresh_data: RefreshTokenRequest):
    payload = AuthService.verify_token(refresh_data.refresh_token, token_type="refresh")
    
    user_id = payload.get("sub")
    email = payload.get("email")
    full_name = payload.get("full_name", "")
    
    token_data = {
        "sub": user_id,
        "email": email,
        "full_name": full_name
    }
    
    access_token = AuthService.create_access_token(token_data)
    
    logger.info(f"Token refreshed for user: {user_id}")
    
    from ..services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    
    try:
        from ..services.auth_service import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")

        current_time = datetime.utcnow().timestamp()
        time_until_expiry = int(exp_timestamp - current_time)
        
        if time_until_expiry > 0:
            # Add token to blacklist
            AuthService.blacklist_token(token, time_until_expiry)
    except Exception as e:
        logger.error(f"Error during logout token blacklisting: {str(e)}")
    
    # Audit log
    logger.info(
        f"User logged out - UserID: {current_user.user_id}, "
        f"Email: {current_user.email}, "
        f"Timestamp: {datetime.utcnow().isoformat()}"
    )
    
    return LogoutResponse(
        message="Successfully logged out",
        user_id=current_user.user_id
    )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user