import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.features.auth.models.user import User
from app.features.auth.utils.password import hash_password
from app.features.auth.utils.emailer import send_password_reset_email


async def request_password_reset(db: AsyncSession, email: str) -> bool:
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # For security, don't reveal if email exists
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="If this email exists, a password reset link has been sent."
        )
    
    # Generate secure reset token (64 characters)
    reset_token = secrets.token_urlsafe(48)
    
    # Set expiry to 30 minutes from now
    reset_token_expiry = datetime.utcnow() + timedelta(minutes=30)
    
    # Save token and expiry to user record
    user.reset_token = reset_token
    user.reset_token_expiry = reset_token_expiry
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request."
        )
    
   
    email_sent = await send_password_reset_email(email, reset_token)
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset email."
        )
    
    return True


async def reset_password(db: AsyncSession, token: str, new_password: str) -> User:

    result = await db.execute(select(User).where(User.reset_token == token))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )
    
    if not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )
    

    hashed_password = hash_password(new_password)
    

    user.password = hashed_password
    user.reset_token = None
    user.reset_token_expiry = None
    user.updated_at = datetime.utcnow()
    
    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password."
        )
    
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
