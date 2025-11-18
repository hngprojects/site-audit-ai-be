from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.auth.schemas.auth import (
    SignupRequest,
    TokenResponse,
    UserResponse
)
from app.features.auth.services.auth_service import AuthService
from app.platform.services.email import send_verification_otp
from app.features.auth.schemas.auth import ResendVerificationRequest


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

# Route for resending verification OTP
@router.post(
    "/resend-verification",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Resend verification OTP",
    description="Request a new OTP to verify code if the original was not received or expired."
)
async def resend_verification_otp(
        request: ResendVerificationRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)

    try:
        username, otp = await auth_service.resend_verification_code(request.email)

        background_tasks.add_task(
            send_verification_otp,
            to_email=request.email,
            username=username,
            otp=otp
        )
        return api_response(
            data={"email": request.email},
            message="Verification code has been resent. Please check your email.",
            status_code=200,
            success=True
        )
    except HTTPException:
        raise