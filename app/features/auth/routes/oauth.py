from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.schemas.auth import GoogleAuthRequest, TokenResponse
from app.features.auth.services.oauth_service import OAuthService
from app.platform.db.session import get_db

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
