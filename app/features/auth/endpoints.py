from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.auth.schemas import (
    ForgetPasswordRequest,
    ResendResetTokenRequest,
    ResetPasswordRequest,
    AuthResponse
)
from app.features.auth.services.auth_service import AuthService
from app.platform.services.email import send_password_reset_email

router = APIRouter()

@router.post("/auth/forgot-password", response_model=AuthResponse)
async def forgot_password(
    request: ForgetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset - generates token and sends email"""
    try:
        auth_service = AuthService(db)

        # Generate reset token with 1-minute expiration
        token, expires_at = await auth_service.generate_reset_token(request.email)

        # Send reset email in background
        background_tasks.add_task(send_password_reset_email, request.email, token)

        return api_response(
            message="Password reset email sent. Link expires in 1 minute.",
            status_code=200,
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process request")

@router.post("/auth/resend-reset-token", response_model=AuthResponse)
async def resend_reset_token(
    request: ResendResetTokenRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Resend reset token if previous one expired"""
    try:
        auth_service = AuthService(db)

        # Generate new reset token
        token, expires_at = await auth_service.generate_reset_token(request.email)

        # Send new reset email
        background_tasks.add_task(send_password_reset_email, request.email, token)

        return api_response(
            message="New password reset email sent. Link expires in 1 minute.",
            status_code=200,
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to resend reset email")

@router.post("/auth/reset-password", response_model=AuthResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using valid token"""
    try:
        auth_service = AuthService(db)

        # Verify token is valid and not expired
        await auth_service.verify_reset_token(request.email, request.token)

        # Update password (this will also clear the reset token)
        await auth_service.update_password(request.email, request.new_password)

        return api_response(
            message="Password reset successfully",
            status_code=200,
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to reset password")
