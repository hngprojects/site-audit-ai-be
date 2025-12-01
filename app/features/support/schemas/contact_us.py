from typing import Optional

from pydantic import BaseModel, EmailStr, Field,validator
import re
PHONE_REGEX = re.compile(r"^\+?[0-9\s\-\(\)]{7,32}$")
class ContactUsRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=15)
    email: EmailStr = Field(...)
    message: str = Field(..., min_length=10, max_length=5000)
    page: Optional[str] = Field(None, description="Page where contact form was submitted")

    @validator("phone_number")
    def validate_phone(cls, value):
        if value and not PHONE_REGEX.match(value):
            raise ValueError("Invalid phone number format.")
        return value