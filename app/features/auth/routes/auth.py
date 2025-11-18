from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.auth.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    UserResponse
)
from app.features.auth.services.auth_service import AuthService
from app.features.auth.utils.security import decode_access_token
from app.platform.services.email import send_verification_otp


router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post(
    "/signup",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, username, and password"
)
async def signup(
    request: SignupRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    - **password**: Minimum 8 characters with at least one uppercase, lowercase, and digit
    Sends verification email in the background.
    """
    auth_service = AuthService(db)
    token_response, otp = await auth_service.register_user(request)
    
    # Print OTP to terminal for debugging
    print(f"OTP for {request.email}: {otp}")
    
    # Send OTP email in background (non-blocking)
    background_tasks.add_task(
        send_verification_otp,
        to_email=request.email,
        username=request.username,
        otp=otp
    )
    
    return api_response(
        data={
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "token_type": token_response.token_type,
            "user": token_response.user.model_dump(mode='json')
        },
        message="User registered successfully. Please check your email for the OTP code to verify your account.",
        status_code=201,
        success=True
    )


@router.post(
    "/login",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate user with email and password"
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    Returns access and refresh tokens.
    """
    auth_service = AuthService(db)
    token_response = await auth_service.login_user(request)
    
    return api_response(
        data={
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "token_type": token_response.token_type,
            "user": token_response.user.model_dump(mode='json')
        },
        message="Login successful",
        status_code=200,
        success=True
    )


@router.post(
    "/logout",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Logout the current user (token-based)"
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout the current user.
    Since we're using JWT tokens, logout is handled client-side by removing the token.
    This endpoint validates the token and confirms logout.
    """
    try:
        # Validate the token
        token = credentials.credentials
        payload = decode_access_token(token)
        
        return api_response(
            data=None,
            message="Logout successful",
            status_code=200,
            success=True
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Dependency to get the current authenticated user.
    Use this in routes that require authentication.
    """
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )