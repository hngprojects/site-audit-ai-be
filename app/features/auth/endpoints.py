from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.schemas.oauth import AuthTokenResponse, GoogleAuthRequest, UserResponse
from app.features.auth.services.oauth_service import OAuthService
from app.features.auth.services.user_service import UserService
from app.platform.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/google", response_model=AuthTokenResponse)
async def google_mobile_auth(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    google_user_info = await OAuthService.verify_google_token(payload.id_token)
    user = await OAuthService.get_or_create_user_from_google(
        db=db,
        google_user_info=google_user_info,
    )
    access_token = UserService.create_access_token(
        data={"sub": str(user.id), "email": user.email}, expires_delta=timedelta(days=7)
    )
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )
