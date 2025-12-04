from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import httpx
import jwt
from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token

# from app.platform.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_ID_ANDROID
from app.platform.config import settings


class GoogleOAuthVerifier:
    """Utility class for verifying Google ID tokens"""

    @staticmethod
    def verify_token(token: str, platform: Optional[str] = "ios") -> dict:
        """
        Verify Google ID token and return user info

        Args:
            token: The ID token from Google Sign-In
            platform: The platform (ios or android) to determine which client ID to use

        Returns:
            Dict containing user info from Google

        Raises:
            HTTPException: If token is invalid
        """
        try:
            client_id = (
                settings.GOOGLE_CLIENT_ID_ANDROID
                if platform and platform.lower() == "android"
                else settings.GOOGLE_CLIENT_ID
            )

            if not client_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Google OAuth not configured",
                )

            idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)

            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                raise ValueError("Wrong issuer.")

            return {
                "provider_user_id": idinfo["sub"],
                "email": idinfo.get("email"),
                "email_verified": idinfo.get("email_verified", False),
                "name": idinfo.get("name"),
                "given_name": idinfo.get("given_name"),
                "family_name": idinfo.get("family_name"),
                "picture": idinfo.get("picture"),
                "locale": idinfo.get("locale"),
            }

        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid Google token: {str(e)}"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to verify Google token: {str(e)}",
            ) from e


class AppleOAuthVerifier:
    """Utility class for working with Apple OAuth (to be implemented)"""

    @staticmethod
    def generate_apple_client_secret() -> str:
        """Generate client secret for Apple OAuth"""
        try:
            with open(settings.APPLE_PRIVATE_KEY_PATH, 'r') as key_file:
                private_key = key_file.read()

            # JWT headers
            headers = {
                "kid": settings.APPLE_KEY_ID,
                "alg": "ES256"
            }

            # JWT payload
            payload = {
                "iss": settings.APPLE_TEAM_ID,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + timedelta(days=180), # 6 months max
                "aud": "https://appleid.apple.com",
                "sub": settings.APPLE_CLIENT_ID
            }

            # Generate the client secret JWT
            client_secret = jwt.encode(
                payload,
                private_key,
                algorithm='ES256',
                headers=headers
            )

            return client_secret

        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Apple private key file not found",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate Apple client secret: {str(e)}",
            )

    @staticmethod
    async def exchange_apple_code_for_tokens(code: str) -> Dict[str, Any]:
        """Exchange the authorization code for tokens from Apple"""
        client_secret = AppleOAuthVerifier.generate_apple_client_secret()
        token_url = "https://appleid.apple.com/auth/token"

        data = {
            "client_id": settings.APPLE_CLIENT_ID,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.APPLE_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Apple token exchange failed: {response.text}",
                    )

                return response.json()

            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"HTTP request to Apple failed: {str(e)}",
                )

    @staticmethod
    def verify_apple_id_token(id_token_str: str) -> Dict[str, Any]:
        """Verify and decode Apple ID token"""
        try:
            # Get Apple's public keys for verification
            jwks_url = "https://appleid.apple.com/auth/keys"
            jwks_client = jwt.PyJWKClient(jwks_url)

            # Get the signing key from the token
            signing_key = jwks_client.get_signing_key_from_jwt(id_token_str)

            # Verify and decode the token
            payload = jwt.decode(
                id_token_str,
                signing_key.key,
                algorithms=["RS256"],
                audience=settings.APPLE_CLIENT_ID,
                issuer="https://appleid.apple.com"
            )

            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Apple ID token has expired",
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to verify Apple ID token: {str(e)}",
            )

    @staticmethod
    def get_apple_authorization_url(state: str = None) -> str:
        """Generate the Apple authorization URL to redirect users for login"""

        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "response_mode": "form_post",
            "client_id": settings.APPLE_CLIENT_ID,
            "redirect_uri": settings.APPLE_REDIRECT_URI,
            "scope": "name email",
        }

        if state:
            params["state"] = state
        base_url = "https://appleid.apple.com/auth/authorize"

        return f"{base_url}?{urlencode(params)}"



