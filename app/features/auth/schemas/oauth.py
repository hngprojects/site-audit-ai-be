from pydantic import BaseModel, EmailStr
from typing import Optional


class AppleUserInfo(BaseModel):
    """User info returned from Apple OAuth"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class AppleCallbackData(BaseModel):
    """Data received from Apple OAuth callback"""
    code: str
    user: Optional[str] = None
    state: Optional[str] = None


class OAuthUserResponse(BaseModel):
    """Response after OAuth authentication"""
    is_new_user: bool
    provider: str


    class Config:
        from_attributes = True