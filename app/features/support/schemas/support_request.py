from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.features.support.models.support_ticket import (
    TicketStatus,
    TicketPriority,
    TicketCategory,
)

class EmailSupportRequest(BaseModel):
    """Schema for email support request"""

    # name: str = Field(..., min_length=2, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    full_name: str | None = Field(None, min_length=2, max_length=255)
    phone_number: str | None = Field(None, min_length=7, max_length=32)
    subject: str = Field(..., min_length=3, max_length=500, description="Support request subject")
    message: str = Field(..., min_length=10, max_length=5000, description="Support request message")
    source: str | None = Field("mobile", description="Origin of the request (mobile/web/api)")



class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ticket_id: str
    email: str
    full_name: str | None
    phone_number: str | None
    subject: str
    message: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    source: str | None
    created_at: datetime
    updated_at: datetime


class TicketStatusUpdate(BaseModel):
    status: TicketStatus = Field(..., description="New status")
