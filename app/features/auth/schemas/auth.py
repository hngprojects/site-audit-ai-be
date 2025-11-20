from pydantic import BaseModel, EmailStr, Field, field_validator, field_serializer
from datetime import datetime
from typing import Optional
import re
import uuid


class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(
        ..., min_length=3, max_length=30, description="Username must be 3-30 characters"
    )
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate and normalize username.

        """
        if not isinstance(v, str):
            raise ValueError("Invalid username")

        v = v.strip()
        if len(v) < 3 or len(v) > 30:
            raise ValueError("Username must be between 3 and 30 characters long")

        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")

        if v[0] in "_-" or v[-1] in "_-":
            raise ValueError("Username cannot start or end with an underscore or hyphen")

        if re.search(r"[_-]{2,}", v):
            raise ValueError("Username cannot contain consecutive underscores or hyphens")

        if v.isdigit():
            raise ValueError("Username cannot be only numbers")

        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_email_verified: bool
    created_at: datetime

    @field_serializer("id")
    def serialize_id(self, value, _info):
        """Convert UUID to string"""
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

    @field_serializer("created_at")
    def serialize_datetime(self, value, _info):
        """Convert datetime to ISO format string"""
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(..., description="ID token from Google Sign-In")
    platform: Optional[str] = Field("ios", description="Platform: ios or android")


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr