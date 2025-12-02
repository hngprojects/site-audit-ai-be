import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactUsRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=20)
    email: EmailStr = Field(...)
    message: str = Field(..., min_length=10, max_length=5000)
    page: Optional[str] = Field(None, description="Page where contact form was submitted")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        """Validate phone number contains only valid characters (no alphabets)"""
        if value is None:
            return value
        
        # Remove whitespace for validation
        cleaned = value.strip()
        
        # Check if phone number contains only digits, spaces, +, -, and parentheses (NO ALPHABETS)
        if not re.match(r'^[\d\s\+\-\(\)]+$', cleaned):
            raise ValueError("Phone number can only contain digits, spaces, +, -, and parentheses. No alphabetic characters allowed.")
        
        # Extract only digits to validate length
        digits_only = re.sub(r'[^\d]', '', cleaned)
        if len(digits_only) < 7:
            raise ValueError("Phone number must contain at least 7 digits")
        
        if len(digits_only) > 15:
            raise ValueError("Phone number cannot exceed 15 digits")
        
        return cleaned