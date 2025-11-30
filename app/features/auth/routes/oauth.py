from typing import Optional

from fastapi import APIRouter, Depends, status, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.features.auth.schemas.auth import GoogleAuthRequest, TokenResponse
from app.features.auth.services.oauth_service import OAuthService
from app.features.auth.utils.oauth import AppleOAuthVerifier
from app.platform.db.session import get_db
from app.platform.response import api_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["Authentication"])


@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with Google",
    description="Authenticate or register a user using Google Sign-In ID token from mobile",
)
async def google_auth(request: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate with Google OAuth

    - **id_token**: The ID token received from Google Sign-In SDK on mobile
    - **platform**: The platform (ios or android) - defaults to ios

    Returns access token, refresh token, and user information
    """
    oauth_service = OAuthService(db)
    token_response = await oauth_service.authenticate_with_google(request)
    return token_response

@router.get(
    "/apple",
    summary="Initiate Apple Sign In",
    description="Redirects user to Apple's authorization page"
)
async def apple_login():
    """ Redirect user to Apple for authentication"""
    auth_url = AppleOAuthVerifier.get_apple_authorization_url()

    logger.info("Redirecting to Apple Sign In URL: %s", auth_url)
    return RedirectResponse(url=auth_url)


@router.post(
    "/apple/callback",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Handle Apple Sign In callback",
    description="Handle the callback from Apple Sign In and authenticate the user"
)
async def apple_callback(
        code: str = Form(...),
        user: Optional[str] = Form(None),
        state: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db)
):
    """ Handle Apple's callback after user authentication """
    try:
        oauth_service = OAuthService(db)

        # Authenticate with Apple
        token_response, is_new_user = await oauth_service.authenticate_with_apple(code, user)
        message = (
            "Account created successfully via Apple Sign In"
            if is_new_user
            else "Logged in successfully via Apple Sign In"
        )

        logger.info(
            f"Apple OAuth {'signup' if is_new_user else 'login'} successful "
            f"for user: {token_response.user.email}"
        )

        return api_response(
            data={
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "user": token_response.user.model_dump(),
                "is_new_user": is_new_user
            },
            message=message,
            status_code=200
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Apple OAuth callback failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Apple OAuth callback processing failed"
        )

@router.get(
    "/apple/auth-url",
    response_model=dict,
    summary="Get Apple Authorization URL",
    description="Returns the Apple authorization URL without redirecting"
)
async def get_auth_url():
    """Alternative endpoint that returns the auth URL as JSON"""
    auth_url = AppleOAuthVerifier.get_apple_authorization_url()

    return api_response(
        data={"authorization_url": auth_url},
        message="Apple authorization URL generated successfully",
        status_code=200
    )