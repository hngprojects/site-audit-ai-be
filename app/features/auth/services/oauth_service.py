from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.features.auth.models.oauth import OAuthAccount
from app.features.auth.models.users import User
from app.features.auth.services.user_service import generate_username_from_email
from app.platform.config import settings


class OAuthService:
    @staticmethod
    async def verify_google_token(token: str) -> dict:
        """
        Verify Google ID token (for mobile apps using Sign-In with Google)

        Args:
            token: ID token from Google Sign-In

        Returns:
            dict: Decoded token payload containing user info

        Raises:
            ValueError: If token is invalid
        """
        try:
            idinfo = id_token.verify_oauth2_token(
                token, requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                raise ValueError("Wrong issuer.")

            return idinfo
        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}") from e

    @staticmethod
    async def get_or_create_user_from_google(
        db: AsyncSession,
        google_user_info: dict,
    ) -> User:
        """
        Get or create a user based on Google user info.

        Args:
            db: AsyncSession - Database session
            google_user_info - User info from Google

        Returns:
            User: The retrieved or newly created user
        """
        provider_user_id = google_user_info.get("sub")
        email = google_user_info.get("email")

        if not provider_user_id or not email:
            raise ValueError("Invalid Google user info")

        # Check if OAuth account exists (with eager loading of user relationship)
        result = await db.execute(
            select(OAuthAccount)
            .where(
                OAuthAccount.provider == "google", OAuthAccount.provider_user_id == provider_user_id
            )
            .options(selectinload(OAuthAccount.user))
        )
        oauth_account = result.scalars().first()

        if oauth_account:
            oauth_account.profile_data = google_user_info
            await db.commit()
            await db.refresh(oauth_account)
            result = await db.execute(select(User).where(User.id == oauth_account.user_id))
            return result.scalar_one()

        # if oauth account does not exist, check if user with email exists
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                username=await generate_username_from_email(email, db),
                first_name=google_user_info.get("given_name"),
                last_name=google_user_info.get("family_name"),
                user_confirmed=google_user_info.get("email_verified", False),
                password=None,  # OAuth users don't need password
            )
            db.add(user)
            await db.flush()

        oauth_account = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=provider_user_id,
            access_token=None,
            refresh_token=None,
            token_expires_at=None,
            profile_data=google_user_info,
        )
        db.add(oauth_account)
        await db.commit()
        await db.refresh(user)
        return user
