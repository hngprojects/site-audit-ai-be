from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ContactUsRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=32)
    email: EmailStr = Field(...)
    message: str = Field(..., min_length=10, max_length=5000)
    page: Optional[str] = Field(None, description="Page where contact form was submitted")
