from typing import Optional

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
