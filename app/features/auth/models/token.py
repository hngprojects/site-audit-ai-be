from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional
from enum import Enum


class ErrorCode(str, Enum):
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_MISSING = "TOKEN_MISSING"
    UNAUTHORIZED = "UNAUTHORIZED"

class ErrorResponse(BaseModel):
    error: str
    error_code: ErrorCode
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = None

class TokenData(BaseModel):
    user_id: str
    email: str
    exp: datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    user_id: str
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        from_attributes = True

class LogoutResponse(BaseModel):
    message: str
    user_id: str