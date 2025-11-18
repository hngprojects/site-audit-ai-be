from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from typing import Optional
import logging


from app.features.auth.models.user import User
from app.features.auth.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserResponse
from app.features.auth.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_otp
)


logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, request: SignupRequest) -> tuple[TokenResponse, str]:

        # Check if email already exists
        email_check = await self.db.execute(
            select(User).where(User.email == request.email.lower())
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if username already exists
        username_check = await self.db.execute(
            select(User).where(User.username == request.username.lower())
        )
        if username_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user with OTP
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)  # OTP valid for 10 minutes
        
        new_user = User(
            email=request.email.lower(),
            username=request.username.lower(),
            password_hash=hash_password(request.password),
            verification_otp=otp,
            otp_expires_at=otp_expiry,
            is_email_verified=False
        )
        
        try:
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or username already exists"
            )
        
        # Generate access and refresh tokens
        access_token = create_access_token(
            data={"sub": str(new_user.id), "email": new_user.email}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(new_user.id), "email": new_user.email}
        )

        # Prepare response - convert UUID to string for Pydantic validation
        user_response = UserResponse(
            id=str(new_user.id),
            email=new_user.email,
            username=new_user.username,
            is_email_verified=new_user.is_email_verified,
            created_at=new_user.created_at
        )

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response
        )

        # Return token response and OTP (for background email sending)
        return token_response, new_user.verification_otp


    async def login_user(self, request: LoginRequest) -> TokenResponse:  
        # Find user by email
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
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        # Generate access and refresh tokens
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # Prepare response - convert UUID to string for Pydantic validation
        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response
        )

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def update_profile(self, user_id: str, first_name: Optional[str], last_name: Optional[str]) -> User:
        """Update user profile information (first_name and last_name)"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def resend_verification_code(self, email:str) -> tuple[str, str]:
        """Resend verification code with rate limiting"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        user = result.scalar_one_or_none()

        logger.info(f"Resend verification attempt for email: {email}")

        if not user:
            logger.warning(f"Resend verification failed - email not found: {email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found"
            )

        if user.is_email_verified:
            logger.warning(f"Resend verification failed - email already verified: {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )

        # Rate limiting: max 5 resends within 1 hour
        now = datetime.utcnow()

        if user.otp_last_resent_at:
            time_since_last_resend = (now  - user.otp_last_resent_at).total_seconds()
            if time_since_last_resend < 60:
                remaining_seconds = int(60 - time_since_last_resend)
                logger.warning(
                    f"Resend verification rate limied (cooldown) - user: {user.id},"
                    f"email: {email}, seconds_since_last: {time_since_last_resend:.2f}"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {remaining_seconds} seconds before requesting a new OTP."
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
                detail="You have exceeded the maximum number of OTP resend attempts. Please try again later."
            )

        # Generate new OTP
        new_otp = generate_otp()
        otp_expiry = now + timedelta(minutes=10)

        user.verification_otp = new_otp
        user.otp_expires_at = otp_expiry
        user.otp_last_resent_at = now

        await self.db.commit()
        await self.db.refresh(user)

        logger.info(
            f"Verification code resent successfully -user: {user.id},"
            f"email: {email}, resend_count: {user.otp_resend_count + 1}"
        )

        return user.username, new_otp



