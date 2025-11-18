from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.auth.schemas.auth import (
    SignupRequest,
    TokenResponse,
    UserResponse,
    ChangePasswordRequest
)
from app.features.auth.services.auth_service import AuthService
from app.platform.services.email import send_verification_otp
from app.features.auth.utils.security import decode_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    "/change-password",
    response_model=dict,
    summary="Change password for authenticated user",
)
async def change_password(
    request: ChangePasswordRequest,
    authorization: str = Depends(lambda: None),
    db: AsyncSession = Depends(get_db)
):
    from fastapi import Header
    from typing import Optional
    
    async def get_current_user(authorization: Optional[str] = Header(None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token = authorization.replace("Bearer ", "")
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            return user_id
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
    
    user_id = await get_current_user(authorization)
    auth_service = AuthService(db)
    
    await auth_service.change_password(
        user_id=user_id,
        current_password=request.current_password,
        new_password=request.new_password
    )
    
    return api_response(
        message="Password changed successfully",
        status_code=200,
        success=True
    )