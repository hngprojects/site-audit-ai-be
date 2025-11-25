import re
from datetime import datetime
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, EmailStr, Field, validator

from app.features.support.models.support_ticket import TicketStatus


class EmailSupportRequest(BaseModel):
    """Schema for email support request"""

    # name: str = Field(..., min_length=2, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    subject: str = Field(..., min_length=3, max_length=500, description="Support request subject")
    message: str = Field(..., min_length=10, max_length=5000, description="Support request message")

    @validator("subject", "message")
    def strip_whitespace(cls, v):
        """Strip leading/trailing whitespace"""
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "email": "john.doe@example.com",
                "subject": "Website Performance Issue",
                "message": "My website is loading very slowly. Can you help?",
            }
        }


class TicketResponse(BaseModel):
    """Schema for ticket response"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    email: str
    subject: str
    message: str
    status: str
    priority: str
    ticket_type: str = "EMAIL"  # Default value
    created_at: datetime
    updated_at: datetime


class TicketStatusUpdate(BaseModel):
    """Schema for updating ticket status"""

    status: TicketStatus = Field(..., description="New ticket status")
    agent_id: Optional[int] = Field(None, description="Agent ID performing the update")


class ValidationService:
    """Validation utilities"""

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Validate email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            return False, "Invalid email format"
        return True, None

    @staticmethod
    def check_spam(message: str, subject: str) -> Tuple[bool, list]:
        """Check for spam indicators"""
        spam_keywords = ["viagra", "casino", "lottery", "click here", "act now"]
        spam_reasons = []

        content = (message + subject).lower()
        for keyword in spam_keywords:
            if keyword in content:
                spam_reasons.append(f"Spam keyword: {keyword}")

        return len(spam_reasons) > 0, spam_reasons
