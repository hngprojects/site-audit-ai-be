
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, time
from typing import Optional

from app.platform.db.session import get_db
from app.features.support.services import ValidationService, TicketService

router = APIRouter(
    prefix="/api/support/phone",
    tags=["Phone Support"]
)


class PhoneSupportInfo(BaseModel):
    """Schema for phone support information"""
    support_line: str
    sales_line: str
    hours: dict
    status: str
    
    class Config:
        schema_extra = {
            "example": {
                "support_line": "+1 (800) 123-4567",
                "sales_line": "+1 (800) 243-4430",
                "hours": {
                    "monday_friday": "9:00 AM - 6:00 PM EST",
                    "saturday_sunday": "10:00 AM - 4:00 PM EST"
                },
                "status": "open"
            }
        }


class CallbackRequest(BaseModel):
    """Schema for callback request"""
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., max_length=50)
    preferred_time: Optional[str] = Field(None, description="Preferred callback time")
    reason: str = Field(..., min_length=10, max_length=500, description="Reason for callback")
    
    @validator('name')
    def validate_name(cls, v):
        import re
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError('Name contains invalid characters')
        return v.strip()
    
    @validator('phone')
    def validate_phone(cls, v):
        is_valid, error = ValidationService.validate_phone(v)
        if not is_valid:
            raise ValueError(error)
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "preferred_time": "Tomorrow afternoon",
                "reason": "Need help with website optimization"
            }
        }


@router.get("/info", response_model=PhoneSupportInfo)
async def get_phone_support_info():
    """
    Get phone support contact information and hours
    
    Returns phone numbers, support hours, and current availability status
    """
    
    # Check if currently within support hours
    now = datetime.now()
    current_time = now.time()
    current_day = now.weekday()  # 0 = Monday, 6 = Sunday
    
    # Define support hours (EST)
    if current_day < 5:  # Monday to Friday
        open_time = time(9, 0)  # 9:00 AM
        close_time = time(18, 0)  # 6:00 PM
    else:  # Saturday and Sunday
        open_time = time(10, 0)  # 10:00 AM
        close_time = time(16, 0)  # 4:00 PM
    
    # Check if currently open
    is_open = open_time <= current_time <= close_time
    
    return PhoneSupportInfo(
        support_line="+1 (800) 123-4567",
        sales_line="+1 (800) 243-4430",
        hours={
            "monday_friday": "9:00 AM - 6:00 PM EST",
            "saturday_sunday": "10:00 AM - 4:00 PM EST"
        },
        status="open" if is_open else "closed"
    )


@router.post("/callback", response_model=dict, status_code=status.HTTP_201_CREATED)
async def request_callback(
    request: CallbackRequest,
    db: Session = Depends(get_db)
):
    # Validate inputs
    is_valid_email, email_error = ValidationService.validate_email(request.email)
    if not is_valid_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=email_error
        )
    
    is_valid_phone, phone_error = ValidationService.validate_phone(request.phone)
    if not is_valid_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=phone_error
        )
    
    # Create ticket for callback request
    ticket_service = TicketService(db)
    
    message = f"Callback Request\n\nPhone: {request.phone}\n"
    if request.preferred_time:
        message += f"Preferred Time: {request.preferred_time}\n"
    message += f"\nReason: {request.reason}"
    
    ticket = ticket_service.create_ticket(
        name=request.name,
        email=request.email,
        subject="Callback Request",
        message=message,
        phone=request.phone,
        ticket_type="callback",
        priority="high",  # Callbacks get higher priority
        source="api",
        category="callback"
    )
    
    return {
        "success": True,
        "message": "Callback request received. We'll call you back soon!",
        "ticket_id": ticket.ticket_id,
        "expected_callback": "within 2 hours during business hours"
    }


@router.get("/hours")
async def get_support_hours():
    """
    Get detailed phone support hours
    
    Returns detailed breakdown of support hours by day
    """
    
    return {
        "timezone": "EST (Eastern Standard Time)",
        "hours": {
            "monday": {"open": "09:00", "close": "18:00", "available": True},
            "tuesday": {"open": "09:00", "close": "18:00", "available": True},
            "wednesday": {"open": "09:00", "close": "18:00", "available": True},
            "thursday": {"open": "09:00", "close": "18:00", "available": True},
            "friday": {"open": "09:00", "close": "18:00", "available": True},
            "saturday": {"open": "10:00", "close": "16:00", "available": True},
            "sunday": {"open": "10:00", "close": "16:00", "available": True}
        },
        "holidays": {
            "closed_on": [
                "New Year's Day",
                "Memorial Day",
                "Independence Day",
                "Labor Day",
                "Thanksgiving",
                "Christmas Day"
            ]
        },
        "emergency_support": {
            "available": True,
            "description": "For urgent technical issues outside business hours, use live chat or email support"
        }
    }


@router.get("/status")
async def get_phone_support_status():
    """
    Get current phone support status
    
    Returns whether phone support is currently available
    """
    
    info = await get_phone_support_info()
    
    return {
        "service": "Phone Support",
        "status": info.status,
        "available": info.status == "open",
        "support_line": info.support_line,
        "alternative_channels": {
            "live_chat": "/api/support/chat/sessions",
            "email": "/api/support/email",
            "message": "/api/support/message"
        }
    }