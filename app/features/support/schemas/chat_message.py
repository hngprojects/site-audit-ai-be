from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime


class ChatSessionCreate(BaseModel):
    """Schema for creating a chat session"""
    user_name: Optional[str] = Field(None, max_length=255, description="User's name")
    user_email: Optional[EmailStr] = Field(None, description="User's email")
    subject: Optional[str] = Field(None, max_length=500, description="Initial query/reason for chat")
    source: str = Field("web", description="Source of chat (web, mobile_app)")
    
    @validator('source')
    def validate_source(cls, v):
        allowed_sources = ['web', 'mobile_app', 'api']
        if v not in allowed_sources:
            raise ValueError(f'Source must be one of: {", ".join(allowed_sources)}')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "user_name": "Damian Amadi",
                "user_email": "damian@example.com",
                "subject": "Need help with Low Readability Score",
                "source": "web"
            }
        }


class ChatSessionResponse(BaseModel):
    """Schema for chat session response"""
    id: int
    session_id: str
    user_name: Optional[str]
    user_email: Optional[str]
    agent_name: Optional[str]
    status: str
    subject: Optional[str]
    queue_position: Optional[int]
    started_at: datetime
    is_active: bool
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "session_id": "CHAT-20241121153045-ABC12345",
                "user_name": "Damian Amadi",
                "user_email": "damian@example.com",
                "agent_name": None,
                "status": "waiting",
                "subject": "Need help with readability",
                "queue_position": 1,
                "started_at": "2024-11-21T15:30:45",
                "is_active": True
            }
        }


class ChatMessageRequest(BaseModel):
    """Schema for sending a chat message"""
    session_id: str = Field(..., description="Chat session ID")
    content: str = Field(..., min_length=1, max_length=2000, description="Message content")
    sender_type: str = Field(..., description="Type of sender (user, agent)")
    sender_name: Optional[str] = Field(None, max_length=255, description="Sender's name")
    
    @validator('sender_type')
    def validate_sender_type(cls, v):
        allowed_types = ['user', 'agent', 'system']
        if v not in allowed_types:
            raise ValueError(f'Sender type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('content')
    def strip_content(cls, v):
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "CHAT-20241121153045-ABC12345",
                "content": "Hi, I just ran an audit on my website, but the report says Low Readability Score, can you explain what that means?",
                "sender_type": "user",
                "sender_name": "Damian Amadi"
            }
        }


class ChatMessageResponse(BaseModel):
    """Schema for chat message response"""
    id: int
    message_id: str
    content: str
    sender_type: str
    sender_name: Optional[str]
    sent_at: datetime
    status: str
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": 1,
                "message_id": "MSG-20241121153100-XYZ98765",
                "content": "Sure, Low Readability Score means that your website text might be too complex...",
                "sender_type": "agent",
                "sender_name": "Support",
                "sent_at": "2024-11-21T15:31:00",
                "status": "sent"
            }
        }


class ChatSessionEnd(BaseModel):
    """Schema for ending a chat session"""
    session_id: str = Field(..., description="Chat session ID to end")
    end_reason: str = Field(..., description="Reason for ending (user_ended, agent_ended, timeout)")
    ended_by: str = Field("user", description="Who ended the session")
    
    @validator('end_reason')
    def validate_end_reason(cls, v):
        allowed_reasons = ['user_ended', 'agent_ended', 'timeout', 'resolved']
        if v not in allowed_reasons:
            raise ValueError(f'End reason must be one of: {", ".join(allowed_reasons)}')
        return v
    
    @validator('ended_by')
    def validate_ended_by(cls, v):
        allowed_values = ['user', 'agent', 'system']
        if v not in allowed_values:
            raise ValueError(f'Ended by must be one of: {", ".join(allowed_values)}')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "CHAT-20241121153045-ABC12345",
                "end_reason": "user_ended",
                "ended_by": "user"
            }
        }


class ChatSessionAssign(BaseModel):
    """Schema for assigning agent to chat session"""
    session_id: str = Field(..., description="Chat session ID")
    agent_id: int = Field(..., description="Agent's user ID")
    agent_name: str = Field(..., max_length=255, description="Agent's name")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "CHAT-20241121153045-ABC12345",
                "agent_id": 1,
                "agent_name": "Jane Support"
            }
        }


class ChatSessionTransfer(BaseModel):
    """Schema for transferring chat session"""
    session_id: str = Field(..., description="Chat session ID")
    new_agent_id: int = Field(..., description="New agent's ID")
    new_agent_name: str = Field(..., max_length=255, description="New agent's name")
    transfer_reason: str = Field(..., max_length=500, description="Reason for transfer")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "CHAT-20241121153045-ABC12345",
                "new_agent_id": 2,
                "new_agent_name": "Senior Support Agent",
                "transfer_reason": "Requires technical expertise"
            }
        }


class ChatSessionRate(BaseModel):
    """Schema for rating a chat session"""
    session_id: str = Field(..., description="Chat session ID")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5 stars")
    feedback: Optional[str] = Field(None, max_length=1000, description="Optional feedback")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "CHAT-20241121153045-ABC12345",
                "rating": 5,
                "feedback": "Very helpful! Resolved my issue quickly."
            }
        }


class MessageListResponse(BaseModel):
    """Schema for list of messages"""
    success: bool
    total: int
    messages: List[ChatMessageResponse]
    
    class Config:
        orm_mode = True


class ChatSessionListResponse(BaseModel):
    """Schema for list of chat sessions"""
    success: bool
    total: int
    sessions: List[ChatSessionResponse]
    
    class Config:
        orm_mode = True