from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Header
from typing import Optional
from datetime import timedelta, datetime
from app.features.auth.models.user import User
from app.features.auth.schemas import AuthResponse,ForgotResetTokenRequest,ForgetPasswordRequest,ResendResetTokenRequest,ResetPasswordRequest
from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.auth.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    ChangePasswordRequest,
    VerifyEmailRequest
)
from app.features.auth.services.auth_service import AuthService,send_password_reset_email
from app.features.auth.utils.security import decode_access_token, generate_otp
from app.platform.services.email import send_verification_otp


blacklisted_tokens = set()
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

    print(f"OTP for {request.email}: {otp}")

    background_tasks.add_task(
        send_verification_otp,
        to_email=request.email,
        username=request.username,
        otp=otp
    )
    
    return api_response(
        data=token_response,
        message="User registered successfully. Please check your email for the OTP code to verify your account.",
        status_code=status.HTTP_201_CREATED
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
        data=token_response,
        message="Login successful",
        status_code=status.HTTP_200_OK
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
        blacklisted_tokens.add(token)

        return api_response(
            data=None,
            message="Logout successful",
            status_code=status.HTTP_200_OK
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
) -> User:
    """
    Dependency to get the current authenticated user.
    """
    try:
        token = credentials.credentials
        if token in blacklisted_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
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

        return user
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

# async def change_password(
#     request: ChangePasswordRequest,
# ):

#     async def get_current_user(authorization: Optional[str] = Header(None)):
#         if not authorization or not authorization.startswith("Bearer "):
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Not authenticated",
#                 headers={"WWW-Authenticate": "Bearer"},
#             )

#         token = authorization.replace("Bearer ", "")
#         try:
#             payload = decode_access_token(token)
#             user_id = payload.get("sub")
#             if not user_id:
#                 raise HTTPException(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                     detail="Invalid authentication credentials"
#                 )
#             return user_id
#         except ValueError as e:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail=str(e)
#             )

#     user_id = await get_current_user(authorization)
#     auth_service = AuthService(db)

#     await auth_service.change_password(
#         user_id=user_id,
#         current_password=request.current_password,
#         new_password=request.new_password
#     )

#     return api_response(
#         message="Password changed successfully",
#         status_code=200,
#     )

@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(
    request: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Reset password using valid token"""
    token = credentials.credentials
    if token in blacklisted_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    try:
        await auth_service.change_password(
            user_id=user.id,
            current_password=request.current_password,
            new_password=request.new_password
        )

        return api_response(
            message="Password changed successfully",
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {e}")


@router.post(
    "/verify-email",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Verify email with OTP",
    description="Verify a user's email address using the OTP sent to their email"
)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user's email with OTP.
    """
    auth_service = AuthService(db)
    await auth_service.verify_email_otp(request.email, request.otp)
    return api_response(
        message="Email verified successfully.",
        status_code=status.HTTP_200_OK
    )
    
@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(
    request: ForgetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset - generates token and sends email"""
    try:
        
        auth_service = AuthService(db)

        # Get user by email and generate reset token with 1-minute expiration
        user = await auth_service.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        verification_otp = generate_otp()

        # Store the token in the database
        user.verification_otp=verification_otp
        user.otp_expires_at=datetime.utcnow() + timedelta(minutes=2)
        await db.commit()

        # Send reset email in background
        background_tasks.add_task(send_password_reset_email, request.email, verification_otp)

        return api_response(
            data={"email": request.email},
            message="Verification code has been resent. Please check your email.",
            status_code=status.HTTP_200_OK
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process request")

@router.post("/resend-reset-token", response_model=AuthResponse)
async def resend_reset_token(
    request: ResendResetTokenRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Resend reset token if previous one expired"""
    try:
        auth_service = AuthService(db)
        
        # Get user by email
        user = await auth_service.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
       
        verification_otp = generate_otp()

        # Store the token in the database
        user.verification_otp=verification_otp
        user.otp_expires_at=datetime.utcnow() + timedelta(minutes=2)
        await db.commit()

        # Send new reset email
        background_tasks.add_task(send_password_reset_email, request.email, verification_otp)

        return api_response(
            message="New password reset email sent. Link expires in 2 minutes.",
            status_code=200,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to resend reset email")

@router.post("/verify-forgot-password", response_model=AuthResponse)
async def reset_password(
    request: ForgotResetTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using valid token"""
    try:
        auth_service = AuthService(db)

        # Verify token is valid and not expired
        await auth_service.verify_otp(request.email, request.token)

        await auth_service.update_password(request.email, request.new_password)

        return api_response(
            message="Password reset successfully",
            status_code=200,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to reset password")
   

