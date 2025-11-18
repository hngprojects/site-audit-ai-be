from pydantic import BaseModel, EmailStr, Field


class RequestPasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address of the user")


class RequestPasswordResetResponse(BaseModel):
    message: str = Field(..., description="Success message")


class ResetPasswordRequest(BaseModel):
    
    token: str = Field(..., description="Reset token from email", min_length=32)
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=128
    )


class ResetPasswordResponse(BaseModel):
    
    message: str = Field(..., description="Success message")
