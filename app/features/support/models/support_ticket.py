from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from uuid_extension import uuid7

from app.platform.db.base import BaseModel


class TicketStatus(str, Enum):
    """Ticket status enumeration"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TicketPriority(str, Enum):
    """Ticket priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketType(str, Enum):
    """Type of support request"""
    EMAIL = "email"
    MESSAGE = "message"
    CALLBACK = "callback"


class SupportTicket(BaseModel):
    __tablename__ = "support_tickets"
    ticket_id = Column(String(50), unique=True, nullable=False, index=True)

    # User information
    # user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)

    # Ticket details
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    ticket_type = Column(SQLEnum(TicketType), nullable=False, default=TicketType.EMAIL)
    priority = Column(SQLEnum(TicketPriority), nullable=False, default=TicketPriority.MEDIUM)
    status = Column(SQLEnum(TicketStatus), nullable=False, default=TicketStatus.PENDING, index=True)

    # Assignment and tracking
    assigned_to = Column(Integer, nullable=True)  # Support agent ID
    category = Column(String(100), nullable=True)  # e.g., "technical", "billing", "general"
    resolved_at = Column(DateTime(timezone=True), nullable=True)  # When ticket was resolved

    # Metadata
    source = Column(String(50), nullable=True)  # "mobile_app", "web", "api"
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<SupportTicket(ticket_id='{self.ticket_id}', email='{self.email}', status='{self.status}')>"

    @classmethod
    def generate_ticket_id(cls):
        """Generate unique ticket ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = str(uuid7())[:8].upper()
        return f"TKT-{timestamp}-{unique_id}"
