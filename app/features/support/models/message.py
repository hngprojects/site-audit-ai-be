"""
Message Model
Handles individual messages in live chat sessions and ticket responses
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SQLEnum, ForeignKey
from app.platform.db.base import BaseModel

class MessageType(str, Enum):
    """Message type enumeration"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"
    AUTO_RESPONSE = "auto_response"


class SenderType(str, Enum):
    """Who sent the message"""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    BOT = "bot"


class MessageStatus(str, Enum):
    """Message delivery status"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class Message(BaseModel):
    __tablename__ = 'messages'
    message_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Relationship to chat session or ticket
    chat_session_id = Column(Integer, nullable=True, index=True)  # FK to live_chat_sessions
    ticket_id = Column(String(50), nullable=True, index=True)  # FK to support_tickets
    
    # Message content
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageType), nullable=False, default=MessageType.TEXT)
    
    # Sender information
    sender_type = Column(SQLEnum(SenderType), nullable=False, index=True)
    sender_id = Column(Integer, nullable=True)  # User ID or Agent ID
    sender_name = Column(String(255), nullable=True)
    sender_email = Column(String(255), nullable=True)
    
    # Recipient information
    recipient_id = Column(Integer, nullable=True)
    recipient_name = Column(String(255), nullable=True)
    
    # Message metadata
    status = Column(SQLEnum(MessageStatus), nullable=False, default=MessageStatus.SENT)
    
    # Timestamps
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Attachments (if any)
    has_attachment = Column(Boolean, default=False, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    attachment_type = Column(String(100), nullable=True)  # mime type
    attachment_size = Column(Integer, nullable=True)  # size in bytes
    
    # Message flags
    is_internal = Column(Boolean, default=False, nullable=False)  # Internal agent notes
    is_automated = Column(Boolean, default=False, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Edit tracking
    edited_at = Column(DateTime, nullable=True)
    original_content = Column(Text, nullable=True)
    
    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    source = Column(String(50), nullable=True)  # "mobile_app", "web", "api"
    
    # Reply/Thread information
    reply_to_message_id = Column(String(100), nullable=True)  # For threaded conversations
    thread_id = Column(String(100), nullable=True)
    
    # Additional data
    metadata = Column(Text, nullable=True)  # JSON string for extra data

    def __repr__(self):
        return f"<Message(message_id='{self.message_id}', sender_type='{self.sender_type}', type='{self.message_type}')>"

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'message_id': self.message_id,
            'chat_session_id': self.chat_session_id,
            'ticket_id': self.ticket_id,
            'content': self.content if not self.is_deleted else '[Message deleted]',
            'message_type': self.message_type.value if self.message_type else None,
            'sender_type': self.sender_type.value if self.sender_type else None,
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'recipient_id': self.recipient_id,
            'recipient_name': self.recipient_name,
            'status': self.status.value if self.status else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'has_attachment': self.has_attachment,
            'attachment': {
                'url': self.attachment_url,
                'name': self.attachment_name,
                'type': self.attachment_type,
                'size': self.attachment_size
            } if self.has_attachment else None,
            'is_internal': self.is_internal,
            'is_automated': self.is_automated,
            'is_edited': self.is_edited,
            'is_deleted': self.is_deleted,
            'edited_at': self.edited_at.isoformat() if self.edited_at else None,
            'reply_to_message_id': self.reply_to_message_id,
            'thread_id': self.thread_id,
            'source': self.source
        }

    @classmethod
    def generate_message_id(cls):
        """Generate unique message ID"""
        import uuid
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"MSG-{timestamp}-{unique_id}"

    def mark_as_read(self):
        """Mark message as read"""
        if self.status != MessageStatus.READ:
            self.status = MessageStatus.READ
            self.read_at = datetime.utcnow()

    def mark_as_delivered(self):
        """Mark message as delivered"""
        if self.status == MessageStatus.SENT:
            self.status = MessageStatus.DELIVERED
            self.delivered_at = datetime.utcnow()

    def soft_delete(self):
        """Soft delete message (keep record but hide content)"""
        self.is_deleted = True
        self.original_content = self.content
        self.content = "[Message deleted]"

    def edit_content(self, new_content):
        """Edit message content"""
        if not self.is_edited:
            self.original_content = self.content
        self.content = new_content
        self.is_edited = True
        self.edited_at = datetime.utcnow()