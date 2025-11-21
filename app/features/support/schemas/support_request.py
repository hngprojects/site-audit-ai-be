
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime


class EmailSupportRequest(BaseModel):
    """Schema for email support request"""
    name: str = Field(..., min_length=2, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    subject: str = Field(..., min_length=3, max_length=500, description="Support request subject")
    message: str = Field(..., min_length=10, max_length=5000, description="Support request message")
    phone: Optional[str] = Field(None, max_length=50, description="Optional phone number")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate name contains only valid characters"""
        import re
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError('Name contains invalid characters')
        return v.strip()
    
    @validator('subject', 'message')
    def strip_whitespace(cls, v):
        """Strip leading/trailing whitespace"""
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "subject": "Website Performance Issue",
                "message": "My website is loading very slowly. Can you help?",
                "phone": "+1234567890"
            }
        }


class MessageRequest(BaseModel):
    """Schema for general message submission"""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    message: str = Field(..., min_length=10, max_length=5000)
    
    @validator('name')
    def validate_name(cls, v):
        import re
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError('Name contains invalid characters')
        return v.strip()
    
    @validator('message')
    def strip_whitespace(cls, v):
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Jane Smith",
                "email": "jane@example.com",
                "message": "I'd like to inquire about your services."
            }
        }


class TicketResponse(BaseModel):
    """Schema for ticket response"""
    id: int
    ticket_id: str
    name: str
    email: str
    subject: str
    message: str
    status: str
    priority: str
    ticket_type: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class EmailSupportResponse(BaseModel):
    """Schema for email support response"""
    success: bool
    message: str
    ticket: TicketResponse
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Support ticket created successfully",
                "ticket": {
                    "id": 1,
                    "ticket_id": "TKT-20241121-ABC12345",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "subject": "Website Issue",
                    "message": "My site is slow",
                    "status": "pending",
                    "priority": "medium",
                    "ticket_type": "email",
                    "created_at": "2024-11-21T10:30:00",
                    "updated_at": "2024-11-21T10:30:00"
                }
            }
        }


class MessageResponse(BaseModel):
    """Schema for message submission response"""
    success: bool
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Message sent successfully. We'll get back to you within 24 hours."
            }
        }


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
    
    class Config:
        schema_extra = {
            "example": {
                "status": "in_progress",
                "agent_id": 1
            }
        }


class TicketResponseAdd(BaseModel):
    """Schema for adding response to ticket"""
    content: str = Field(..., min_length=1, max_length=5000)
    sender_name: Optional[str] = Field(None, max_length=255)
    is_internal: bool = Field(False, description="Whether this is an internal note")
    
    class Config:
        schema_extra = {
            "example": {
                "content": "We're investigating this issue and will update you soon.",
                "sender_name": "Support Agent",
                "is_internal": False
            }
        }


class TicketSearchParams(BaseModel):
    """Schema for ticket search parameters"""
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    search_term: Optional[str] = None
    user_email: Optional[str] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "pending",
                "priority": "high",
                "limit": 20,
                "offset": 0
            }
        }


class TicketListResponse(BaseModel):
    """Schema for ticket list response"""
    success: bool
    total: int
    tickets: List[TicketResponse]
    
    class Config:
        orm_mode = True