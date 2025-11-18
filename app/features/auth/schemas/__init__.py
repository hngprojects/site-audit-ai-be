from pydantic import BaseModel, EmailStr
from datetime import datetime

class ForgetPasswordRequest(BaseModel):
    email: EmailStr

class ResendResetTokenRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str

class AuthResponse(BaseModel):
    message: str
    success: bool = True
