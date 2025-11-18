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
from app.features.auth.services import (
    generate_reset_token,
    send_reset_email,
    verify_reset_token,
    update_password,
    clear_reset_token
)

router = APIRouter()

@router.post("/auth/forgot-password", response_model=AuthResponse)
async def forgot_password(
    request: ForgetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset - generates token and sends email"""
    try:
        # Generate reset token with 1-minute expiration
        token, expires_at = await generate_reset_token(db, request.email)

        # Send reset email in background
        background_tasks.add_task(send_reset_email, request.email, token)

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
        # Generate new reset token
        token, expires_at = await generate_reset_token(db, request.email)

        # Send new reset email
        background_tasks.add_task(send_reset_email, request.email, token)

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
        # Verify token is valid and not expired
        await verify_reset_token(db, request.email, request.token)

        # Update password (this will also clear the reset token)
        await update_password(db, request.email, request.new_password)

        # Clear reset token
        await clear_reset_token(db, request.email)

        return api_response(
            message="Password reset successfully",
            status_code=200,
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to reset password")
