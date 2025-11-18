from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class GoogleAuthRequest(BaseModel):
    """Request schema for Google Sign-In (Mobile)"""

    id_token: str = Field(..., description="ID token from Google Sign-In")


class GoogleAuthWebRequest(BaseModel):
    """Request schema for Google OAuth (Web)"""

    code: str = Field(..., description="Authorization code from Google OAuth")
    redirect_uri: str = Field(..., description="Redirect URI used in the OAuth flow")


class OAuthAccountResponse(BaseModel):
    """Response schema for OAuth account"""

    id: UUID
    provider: str
    provider_user_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuthTokenResponse(BaseModel):
    """Response schema for authentication"""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    """Response schema for user"""

    id: UUID
    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_confirmed: bool
    created_at: datetime

    class Config:
        from_attributes = True
