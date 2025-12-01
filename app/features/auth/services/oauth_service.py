import json
from datetime import datetime
from typing import Optional, Tuple
import logging

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
from app.features.auth.utils.oauth import AppleOAuthVerifier


logger = logging.getLogger(__name__)

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

    # For Apple OAuth, similar methods would be implemented here
    async def get_oauth_connections(self, provider: str, provider_user_id: str) -> Optional[OAuthAccount]:
        """Get OAuth connection by provider and provider user ID"""
        result = await self.db.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())

        )
        return result.scalar_one_or_none()

    async def create_oauth_user(
            self,
            email: str,
            provider: str,
            provider_user_id: str,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            provider_email: Optional[str] = None,
    ) -> Tuple[User, bool]:
        """Create a new user from oauth data or link to existing user"""
        # Check if user with email exists
        existing_user = await self.get_user_by_email(email)

        # If user exists, link OAuth account
        if existing_user:
            oauth_account = OAuthAccount(
                user_id=existing_user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                provider_email=provider_email or email,
            )
            self.db.add(oauth_account)
            await self.db.commit()

            logger.info(f"Linked {provider} account to existing user {existing_user.id}")
            return existing_user, False

        # Create a new user
        # Generate username from email or name
        username_base = email.split('@')[0]
        username = username_base
        counter = 1

        # Ensure username is unique
        while True:
            result = await self.db.execute(
                select(User).where(User.username == username.lower())
            )
            if not result.scalar_one_or_none():
                break
            username = f"{username_base}{counter}"
            counter += 1

        new_user = User(
            email=email.lower(),
            username=username.lower(),
            first_name=first_name,
            last_name=last_name,
            password_hash=None,
            is_email_verified=True,
            email_verified_at=None
        )

        self.db.add(new_user)
        await self.db.flush()  # Get new user ID

        # Create OAuth connection
        oauth_connection = OAuthAccount(
            user_id=new_user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email or email,
        )

        self.db.add(oauth_connection)
        await self.db.commit()
        await self.db.refresh(new_user)

        logger.info(f"Created new user via {provider}: {new_user.id}")
        return new_user, True

    async def authenticate_with_apple(
            self,
            code: str,
            user_data_json: Optional[str] = None,
    ) -> Tuple[TokenResponse, bool]:
        """Authenticate user with Apple OAuth"""
        # 1. Exchange code for tokens
        token_response = await AppleOAuthVerifier.exchange_apple_code_for_tokens(code)
        id_token = token_response.get('id_token')

        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token returned from Apple"
            )

        # 2. Verify and decode ID token
        user_info = AppleOAuthVerifier.verify_apple_id_token(id_token)

        apple_user_id = user_info.get('sub')
        email = user_info.get('email')
        email_verified = user_info.get('email_verified', False)

        if not apple_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user ID in Apple ID token"
            )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No email in Apple ID token"
            )

        # 3. Parse user name data (only sent on first authorization)
        first_name = None
        last_name = None

        if user_data_json:
            try:
                user_data = json.loads(user_data_json)
                name_data = user_data.get('name', {})
                first_name = name_data.get('firstName')
                last_name = name_data.get('lastName')
            except json.JSONDecodeError:
                logger.warning("Failed to parse Apple user data JSON")

        # 4. Check for existing OAuth connection
        oauth_connect = await self.get_oauth_connections("apple", apple_user_id)
        if oauth_connect:
            # Existing user - login
            result = await self.db.execute(
                select(User).where(User.id == oauth_connect.user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            is_new_user = False
            logger.info(f"Apple OAuth login for existing user {user.id}")

        else:
            # New user - create account
            user, is_new_user = await self.create_oauth_user(
                email=email,
                provider="apple",
                provider_user_id=apple_user_id,
                first_name=first_name,
                last_name=last_name,
                provider_email=email
            )

        # 5. Generate apple tokens
        access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
        refresh_token = create_refresh_token(data={"sub": str(user.id), "email": user.email})

        # Prepare response
        user_response = UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at,
        )

        token_response_obj = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response,
        )

        return token_response_obj, is_new_user


