from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db.session import get_db
from app.features.auth.schemas.password_reset import (
    RequestPasswordResetRequest,
    RequestPasswordResetResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.features.auth.services.password_reset import (
    request_password_reset,
    reset_password,
)
from app.features.auth.utils.emailer import send_password_reset_confirmation_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/request-password-reset",
    response_model=RequestPasswordResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Request a password reset link to be sent via email"
)
async def request_password_reset_endpoint(
    request: RequestPasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        await request_password_reset(db, request.email)
        return RequestPasswordResetResponse(
            message="If this email exists, a password reset link has been sent."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request."
        )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password",
    description="Reset password using a valid reset token"
)
async def reset_password_endpoint(
    request: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await reset_password(db, request.token, request.new_password)
        

        background_tasks.add_task(
            send_password_reset_confirmation_email,
            user.email
        )
        
        return ResetPasswordResponse(
            message="Password has been reset successfully."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting your password."
        )
