import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.user import User
from app.features.auth.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse
from app.features.auth.utils.security import (
    create_access_token,
    create_refresh_token,
    generate_otp,
    hash_password,
    verify_password,
)
from app.platform.services.email import send_email

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, request: SignupRequest) -> tuple[TokenResponse, str]:

        email_check = await self.db.execute(
            select(User).where(User.email == request.email.lower())
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )

        username_check = await self.db.execute(
            select(User).where(User.username == request.username.lower())
        )
        if username_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )
        
       
        
        new_user = User(
            email=request.email.lower(),
            username=request.username.lower(),
            password_hash=hash_password(request.password),
            is_email_verified=True,
        )

        try:
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email or username already exists"
            )

        access_token = create_access_token(
            data={"sub": str(new_user.id), "email": new_user.email}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(new_user.id), "email": new_user.email}
        )

        user_response = UserResponse(
            id=str(new_user.id),
            email=new_user.email,
            username=new_user.username,
            is_email_verified=new_user.is_email_verified,
            created_at=new_user.created_at,
        )

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response,
        )

        return token_response, new_user.verification_otp


    async def login_user(self, request: LoginRequest) -> TokenResponse:  
        result = await self.db.execute(
            select(User).where(User.email == request.email.lower())
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user.last_login = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)

        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})

        # Prepare response - convert UUID to string for Pydantic validation
        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response,
        )

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID (accepts UUID string)"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def update_profile(
        self, user_id: str, first_name: Optional[str], last_name: Optional[str]
    ) -> User:
        """Update user profile information (first_name and last_name)"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def verify_otp(self, email: str, otp: str) -> bool:
        """Verify that the reset token is valid and not expired"""
        # Find user by email
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check if token matches and hasn't expired
        if (
            user.verification_otp != otp
            or not user.otp_expires_at
            or user.otp_expires_at < datetime.utcnow()
        ):
            logger.warning(
                f"Password reset verification failed - invalid or expired OTP - user: {user.id}, email: {email}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
            )

        return True

    async def update_password(self, email: str, new_password: str) -> None:
        """Update user password and clear reset token"""
        # Find user by email
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Hash new password and update
        user.password_hash = hash_password(new_password)
        user.verification_otp = None
        user.otp_expires_at = None

        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"Password reset successful - user: {user.id}, email: {email}")

    async def clear_reset_token(self, email: str) -> None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if user:
            user.password_reset_token = None
            user.password_reset_expires_at = None
            await self.db.commit()

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
            )

        if current_password == new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        user.password_hash = hash_password(new_password)
        await self.db.commit()
        await self.db.refresh(user)

    async def verify_email_otp(self, email: str, otp: str) -> None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_email_verified:
            raise HTTPException(status_code=400, detail="Email already verified")
        if user.verification_otp != otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        if not user.otp_expires_at or user.otp_expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="OTP expired")

        user.is_email_verified = True
        user.email_verified_at = datetime.utcnow()
        user.verification_otp = None
        user.otp_expires_at = None
        await self.db.commit()
        await self.db.refresh(user)

    async def resend_verification_code(self, email: str) -> tuple[str, str]:
        """Resend verification code with rate limiting"""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        logger.info(f"Resend verification attempt for email: {email}")

        if not user:
            logger.warning(f"Resend verification failed - email not found: {email}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")

        if user.is_email_verified:
            logger.warning(f"Resend verification failed - email already verified: {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified"
            )

        now = datetime.utcnow()

        if user.otp_last_resent_at:
            time_since_last_resend = (now - user.otp_last_resent_at).total_seconds()
            if time_since_last_resend < 60:
                remaining_seconds = int(60 - time_since_last_resend)
                logger.warning(
                    f"Resend verification rate limied (cooldown) - user: {user.id},"
                    f"email: {email}, seconds_since_last: {time_since_last_resend:.2f}"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {remaining_seconds} seconds before requesting a new OTP.",
                )

        # Rate count if last resend was more than an hour ago
        one_hour_ago = now - timedelta(hours=1)
        if user.otp_last_resent_at and user.otp_last_resent_at < one_hour_ago:
            user.otp_resend_count = 0

        # Check if resend limit exceeded
        if user.otp_resend_count >= 3:
            logger.warning(
                f"Resend verification rate limied (hourly max) - user: {user.id},"
                f"email: {email}, resend_count: {user.otp_resend_count}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You have exceeded the maximum number of OTP resend attempts. Please try again later.",
            )

        # Generate new OTP
        new_otp = generate_otp()
        otp_expiry = now + timedelta(minutes=10)

        user.verification_otp = new_otp
        user.otp_expires_at = otp_expiry
        user.otp_last_resent_at = now
        user.otp_resend_count += 1

        await self.db.commit()
        await self.db.refresh(user)

        logger.info(
            f"Verification code resent successfully -user: {user.id},"
            f"email: {email}, resend_count: {user.otp_resend_count + 1}"
        )

        return user.username, new_otp


def send_password_reset_email(to_email: str, otp: str):
    """Send password reset email to user"""
    subject = "Password Reset Request - Site Audit AI"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #FF6B35;">Password Reset Request</h2>
                <p>Hi there,</p>
                <p>We received a request to reset your password for your Site Audit AI account. If you made this request, please use the OTP code below:</p>

                <div style="text-align: center; margin: 30px 0;">
                    <div style="background-color: #f5f5f5; 
                                padding: 20px; 
                                border-radius: 10px;
                                display: inline-block;">
                        <p style="margin: 0; font-size: 14px; color: #666;">Your OTP Code</p>
                        <h1 style="margin: 10px 0; 
                                   font-size: 36px; 
                                   letter-spacing: 8px;
                                   color: #FF6B35;
                                   font-weight: bold;">{otp}</h1>
                    </div>
                </div>

                <p style="color: #666; font-size: 14px; margin-top: 30px;">
                    This OTP will expire in <strong>10 minutes</strong>. If you didn't request a password reset, please ignore this email.
                </p>

                <p style="color: #999; font-size: 12px; margin-top: 20px;">
                    <strong>Security Tip:</strong> Never share this OTP with anyone. Site Audit AI will never ask for your OTP via phone or email.
                </p>

                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    &copy; 2025 Site Audit AI. All rights reserved.
                </p>
            </div>
        </body>
    </html>
    """

    send_email(to_email, subject, body)
