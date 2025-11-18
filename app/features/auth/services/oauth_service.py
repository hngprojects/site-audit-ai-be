from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.oauth import OAuthAccount
from app.features.auth.models.user import User
from app.features.auth.schemas.auth import GoogleAuthRequest, TokenResponse, UserResponse
from app.features.auth.utils.oauth import GoogleOAuthVerifier
from app.features.auth.utils.security import create_access_token, create_refresh_token
from app.features.auth.utils.username_generator import generate_unique_username


class OAuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_with_google(self, request: GoogleAuthRequest) -> TokenResponse:
        """
        Authenticate user with Google ID token

        Args:
            request: GoogleAuthRequest containing id_token and platform

        Returns:
            TokenResponse with access token, refresh token, and user info
        """
        google_user_info = GoogleOAuthVerifier.verify_token(request.id_token, request.platform)

        provider_user_id = google_user_info["provider_user_id"]
        email = google_user_info["email"]
        email_verified = google_user_info.get("email_verified", False)

        oauth_result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == "google", OAuthAccount.provider_user_id == provider_user_id
            )
        )
        oauth_account = oauth_result.scalar_one_or_none()

        if oauth_account:
            user = await self._get_user_by_id(oauth_account.user_id)

            user.last_login = datetime.utcnow()
            oauth_account.provider_data = google_user_info
            oauth_account.provider_email = email

            await self.db.commit()
            await self.db.refresh(user)

        else:
            user_result = await self.db.execute(select(User).where(User.email == email.lower()))
            user = user_result.scalar_one_or_none()

            if user:
                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_user_id=provider_user_id,
                    provider_email=email,
                    provider_data=google_user_info,
                )

                if email_verified and not user.is_email_verified:
                    user.is_email_verified = True
                    user.email_verified_at = datetime.utcnow()

                user.last_login = datetime.utcnow()

                self.db.add(oauth_account)
                await self.db.commit()
                await self.db.refresh(user)

            else:
                username = await generate_unique_username(email, self.db)

                user = User(
                    email=email.lower(),
                    username=username,
                    password_hash=None,  # No password for OAuth users
                    first_name=google_user_info.get("given_name"),
                    last_name=google_user_info.get("family_name"),
                    is_email_verified=email_verified,
                    email_verified_at=datetime.utcnow() if email_verified else None,
                    last_login=datetime.utcnow(),
                )

                self.db.add(user)
                await self.db.flush()  # Flush to get the user ID

                oauth_account = OAuthAccount(
                    user_id=user.id,
                    provider="google",
                    provider_user_id=provider_user_id,
                    provider_email=email,
                    provider_data=google_user_info,
                )

                self.db.add(oauth_account)

                try:
                    await self.db.commit()
                    await self.db.refresh(user)
                except IntegrityError as e:
                    await self.db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to create user account",
                    ) from e

        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})

        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response,
        )

    async def _get_user_by_id(self, user_id: str) -> User:
        """Helper method to get user by ID"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
