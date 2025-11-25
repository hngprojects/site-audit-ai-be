from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
import re

class ForgetPasswordRequest(BaseModel):
    email: EmailStr

class ResendResetTokenRequest(BaseModel):
    email: EmailStr
    
    
class ForgotResetTokenRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        return v

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    old_password: str
    new_password: str

class AuthResponse(BaseModel):
    message: str
    success: bool = True
