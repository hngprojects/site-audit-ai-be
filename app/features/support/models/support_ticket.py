from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Column, Integer, String, Text
from uuid_extension import uuid7

from app.platform.db.base import BaseModel



class TicketStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, Enum):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCOUNT = "account"
    GENERAL = "general"


def make_ticket_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"TKT-{timestamp}-{str(uuid7()).upper()}"


class SupportTicket(BaseModel):
    __tablename__ = "support_tickets"
    ticket_id = Column(
            String(50), 
            unique=True, 
            nullable=False, 
            index=True,
            default=make_ticket_id
        )

    email = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(
        SQLEnum(TicketPriority), 
        nullable=False, 
        default=TicketPriority.MEDIUM
    )
    status = Column(
        SQLEnum(TicketStatus), 
        nullable=False, 
        default=TicketStatus.PENDING, 
        index=True
    )
    assigned_to = Column(Integer, nullable=True)  # Support agent ID
    category = Column(
        SQLEnum(TicketCategory, name="ticket_category"),
        nullable=False,
        default=TicketCategory.GENERAL,
    )
    notes = Column(Text, nullable=True)
    

    def __repr__(self):
        return f"<SupportTicket(ticket_id='{self.ticket_id}', email='{self.email}', status='{self.status}')>"
