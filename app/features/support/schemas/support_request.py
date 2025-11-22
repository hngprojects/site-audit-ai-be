
from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict
from typing import Optional, List
from datetime import datetime


class EmailSupportRequest(BaseModel):
    """Schema for email support request"""
    #name: str = Field(..., min_length=2, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    subject: str = Field(..., min_length=3, max_length=500, description="Support request subject")
    message: str = Field(..., min_length=10, max_length=5000, description="Support request message")
    #phone: Optional[str] = Field(None, max_length=50, description="Optional phone number")
    
    # @validator('name')
    # def validate_name(cls, v):
    #     """Validate name contains only valid characters"""
    #     import re
    #     if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
    #         raise ValueError('Name contains invalid characters')
    #     return v.strip()
    
    @validator('subject', 'message')
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
    #name: str
    email: str
    subject: str
    message: str
    status: str
    priority: str
    ticket_type: str = "EMAIL" #Default value
    created_at: datetime
    updated_at: datetime


class EmailSupportResponse(BaseModel):
    """Schema for email support response"""
    success: bool
    message: str
    ticket: TicketResponse
 
class TicketStatusUpdate(BaseModel):
    """Schema for updating ticket status"""
    status: str = Field(..., description="New ticket status")
    agent_id: Optional[int] = Field(None, description="Agent ID performing the update")
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'in_progress', 'resolved', 'closed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v
