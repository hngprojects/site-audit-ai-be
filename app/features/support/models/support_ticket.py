from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum
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


# class TicketType(str, Enum):
#     """Type of support request"""
#     EMAIL = "email"
#     MESSAGE = "message"
#     CALLBACK = "callback"


class SupportTicket(BaseModel):
    __tablename__ = 'support_tickets'
    ticket_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # User information
    user_id = Column(Integer, nullable=True, index=True)  # If user is authenticated
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    
    # Ticket details
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    # ticket_type = Column(SQLEnum(TicketType), nullable=False, default=TicketType.EMAIL)
    priority = Column(SQLEnum(TicketPriority), nullable=False, default=TicketPriority.MEDIUM)
    status = Column(SQLEnum(TicketStatus), nullable=False, default=TicketStatus.PENDING, index=True)
    
    # Assignment and tracking
    assigned_to = Column(Integer, nullable=True)  # Support agent ID
    category = Column(String(100), nullable=True)  # e.g., "technical", "billing", "general"
    
    # Timestamps
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Metadata
    source = Column(String(50), nullable=True)  # "mobile_app", "web", "api"
    notes = Column(Text, nullable=True)
    
    # # Response tracking
    # first_response_at = Column(DateTime, nullable=True)
    # response_count = Column(Integer, default=0, nullable=False)
    
    # # Additional data (JSON serializable)
    # tags = Column(Text, nullable=True)  # Comma-separated tags
    # notes = Column(Text, nullable=True)  # Internal notes from support agents

    def __repr__(self):
        return f"<SupportTicket(ticket_id='{self.ticket_id}', email='{self.email}', status='{self.status}')>"

    # def to_dict(self):
    #     """Convert model to dictionary"""
    #     return {
    #         'id': self.id,
    #         'ticket_id': self.ticket_id,
    #         'user_id': self.user_id,
    #         'name': self.name,
    #         'email': self.email,
    #         'phone': self.phone,
    #         'subject': self.subject,
    #         'message': self.message,
    #         'ticket_type': self.ticket_type.value if self.ticket_type else None,
    #         'priority': self.priority.value if self.priority else None,
    #         'status': self.status.value if self.status else None,
    #         'assigned_to': self.assigned_to,
    #         'category': self.category,
    #         'created_at': self.created_at.isoformat() if self.created_at else None,
    #         'updated_at': self.updated_at.isoformat() if self.updated_at else None,
    #         'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
    #         'closed_at': self.closed_at.isoformat() if self.closed_at else None,
    #         'source': self.source,
    #         'first_response_at': self.first_response_at.isoformat() if self.first_response_at else None,
    #         'response_count': self.response_count,
    #         'tags': self.tags.split(',') if self.tags else [],
    #         'notes': self.notes
    #     }

    @classmethod
    def generate_ticket_id(cls):
        """Generate unique ticket ID"""
        import uuid
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"TKT-{timestamp}-{unique_id}"