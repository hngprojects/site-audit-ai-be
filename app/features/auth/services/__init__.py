import secrets
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from app.platform.services.email import send_email
from app.platform.config import MAIL_FROM_NAME

# Assuming User model exists with these fields:
# email: str
# reset_token: str (nullable)
# reset_token_expires: datetime (nullable)

async def generate_reset_token(db: AsyncSession, email: str):
    """Generate a secure reset token and set 1-minute expiration"""
    # This would need to be imported when User model exists
    # from app.features.auth.models.user import User

    # For now, we'll assume the User model exists
    # user = await db.execute(select(User).where(User.email == email))
    # user = user.scalar_one_or_none()

    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")

    # Generate secure token
    token = secrets.token_urlsafe(32)

    # Set 1-minute expiration
    expires_at = datetime.utcnow() + timedelta(minutes=1)

    # Update user with token and expiration
    # user.reset_token = token
    # user.reset_token_expires = expires_at
    # await db.commit()

    return token, expires_at

async def send_reset_email(email: str, token: str):
    """Send password reset email"""
    subject = "Password Reset Request"
    reset_link = f"https://yourapp.com/reset-password?token={token}&email={email}"
    body = f"""
    Hi,

    You requested a password reset for your account.

    Click this link to reset your password: {reset_link}

    This link will expire in 1 minute for security reasons.

    If you didn't request this reset, please ignore this email.

    Best regards,
    {MAIL_FROM_NAME}
    """

    try:
        send_email(email, subject, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send reset email")

async def verify_reset_token(db: AsyncSession, email: str, token: str):
    """Verify if reset token is valid and not expired"""
    # This would need User model import
    # user = await db.execute(select(User).where(
    #     User.email == email,
    #     User.reset_token == token
    # ))
    # user = user.scalar_one_or_none()

    # if not user:
    #     raise HTTPException(status_code=400, detail="Invalid reset token")

    # if user.reset_token_expires < datetime.utcnow():
    #     raise HTTPException(status_code=400, detail="Reset token has expired")

    # return user

    # For now, return mock success
    return True

async def update_password(db: AsyncSession, email: str, new_password: str):
    """Update user password after successful reset"""
    # This would hash the password and update the user
    # user = await verify_reset_token(db, email, token)  # Already verified
    # user.password_hash = hash_password(new_password)
    # user.reset_token = None
    # user.reset_token_expires = None
    # await db.commit()

    pass

async def clear_reset_token(db: AsyncSession, email: str):
    """Clear reset token after successful password update"""
    # user = await db.execute(select(User).where(User.email == email))
    # user = user.scalar_one_or_none()
    # if user:
    #     user.reset_token = None
    #     user.reset_token_expires = None
    #     await db.commit()

    pass
