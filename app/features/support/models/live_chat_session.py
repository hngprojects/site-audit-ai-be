from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum, Text
from app.platform.db.base import BaseModel

class ChatStatus(str, Enum):
    """Chat session status"""
    WAITING = "waiting"  # User waiting for agent
    ACTIVE = "active"    # Conversation in progress
    ENDED = "ended"      # Chat ended by user or agent
    TIMEOUT = "timeout"  # Session timed out
    TRANSFERRED = "transferred"  # Transferred to another agent


class LiveChatSession(BaseModel):
    __tablename__ = 'live_chat_sessions'

    session_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Participant information
    user_id = Column(Integer, nullable=True, index=True)  # Authenticated user ID
    user_name = Column(String(255), nullable=True)
    user_email = Column(String(255), nullable=True)
    agent_id = Column(Integer, nullable=True, index=True)  # Support agent ID
    agent_name = Column(String(255), nullable=True)
    
    # Session details
    status = Column(SQLEnum(ChatStatus), nullable=False, default=ChatStatus.WAITING, index=True)
    subject = Column(String(500), nullable=True)  # Initial query/reason
    category = Column(String(100), nullable=True)
    
    # Queue management
    queue_position = Column(Integer, nullable=True)
    wait_time_seconds = Column(Integer, default=0)  # Time spent waiting for agent
    
    # Timing information
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    agent_joined_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Session metadata
    source = Column(String(50), nullable=True)  # "mobile_app", "web"
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_info = Column(Text, nullable=True)
    
    # Chat metrics
    message_count = Column(Integer, default=0, nullable=False)
    user_message_count = Column(Integer, default=0, nullable=False)
    agent_message_count = Column(Integer, default=0, nullable=False)
    
    # Session quality
    rating = Column(Integer, nullable=True)  # 1-5 star rating
    feedback = Column(Text, nullable=True)
    
    # Flags
    is_active = Column(Boolean, default=True, nullable=False)
    is_transferred = Column(Boolean, default=False, nullable=False)
    requires_followup = Column(Boolean, default=False, nullable=False)
    
    # Related ticket
    ticket_id = Column(String(50), nullable=True)  # If escalated to ticket
    
    # Notes
    internal_notes = Column(Text, nullable=True)
    transfer_reason = Column(Text, nullable=True)
    end_reason = Column(String(255), nullable=True)  # "user_ended", "agent_ended", "timeout", etc.

    def __repr__(self):
        return f"<LiveChatSession(session_id='{self.session_id}', status='{self.status}', agent_id={self.agent_id})>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_email': self.user_email,
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'status': self.status.value if self.status else None,
            'subject': self.subject,
            'category': self.category,
            'queue_position': self.queue_position,
            'wait_time_seconds': self.wait_time_seconds,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'agent_joined_at': self.agent_joined_at.isoformat() if self.agent_joined_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'source': self.source,
            'message_count': self.message_count,
            'user_message_count': self.user_message_count,
            'agent_message_count': self.agent_message_count,
            'rating': self.rating,
            'feedback': self.feedback,
            'is_active': self.is_active,
            'is_transferred': self.is_transferred,
            'requires_followup': self.requires_followup,
            'ticket_id': self.ticket_id,
            'end_reason': self.end_reason
        }

    @classmethod
    def generate_session_id(cls):
        """Generate unique session ID"""
        import uuid
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"CHAT-{timestamp}-{unique_id}"

    def calculate_duration(self):
        """Calculate chat duration in seconds"""
        if self.ended_at and self.started_at:
            return int((self.ended_at - self.started_at).total_seconds())
        elif self.started_at:
            return int((datetime.utcnow() - self.started_at).total_seconds())
        return 0

    def calculate_response_time(self):
        """Calculate average response time"""
        if self.agent_joined_at and self.started_at:
            return int((self.agent_joined_at - self.started_at).total_seconds())
        return None

    def is_stale(self, timeout_minutes=30):
        """Check if session has timed out due to inactivity"""
        if not self.is_active:
            return False
        
        time_diff = (datetime.utcnow() - self.last_activity_at).total_seconds()
        return time_diff > (timeout_minutes * 60)