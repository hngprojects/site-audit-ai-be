from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.features.support.models import SupportTicket, Message
from app.features.support.models.support_ticket import TicketStatus, TicketPriority, TicketType
from app.features.support.models.message import MessageType, SenderType


class TicketService:
    """Service for managing support tickets"""
    
    # SLA configurations (in hours)
    SLA_RESPONSE_TIME = {
        'urgent': 1,
        'high': 4,
        'medium': 24,
        'low': 48
    }
    
    def __init__(self, db: Session):

        self.db = db
    
    def create_ticket(
        self,
        name: str,
        email: str,
        subject: str,
        message: str,
        ticket_type: str = "email",
        priority: str = "medium",
        phone: Optional[str] = None,
        user_id: Optional[int] = None,
        source: str = "web",
        category: Optional[str] = None
    ) -> SupportTicket:
        # Auto-prioritize based on keywords
        if not priority or priority == "medium":
            priority = self._auto_detect_priority(subject, message)
        
        ticket = SupportTicket(
            ticket_id=SupportTicket.generate_ticket_id(),
            user_id=user_id,
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
            ticket_type=TicketType(ticket_type),
            priority=TicketPriority(priority),
            status=TicketStatus.PENDING,
            source=source,
            category=category or self._auto_categorize(subject, message),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        
        return ticket
    
    def get_ticket(self, ticket_id: int) -> Optional[SupportTicket]:
        return self.db.query(SupportTicket).filter(
            SupportTicket.id == ticket_id
        ).first()
    
    def get_ticket_by_ticket_id(self, ticket_id_str: str) -> Optional[SupportTicket]:
        return self.db.query(SupportTicket).filter(
            SupportTicket.ticket_id == ticket_id_str
        ).first()
    
    def update_ticket_status(
        self,
        ticket_id: int,
        new_status: str,
        agent_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        ticket = self.get_ticket(ticket_id)
        
        if not ticket:
            return False, "Ticket not found"
        
        old_status = ticket.status
        ticket.status = TicketStatus(new_status)
        ticket.updated_at = datetime.utcnow()
        
        # Set timestamps based on status
        if new_status == "in_progress" and old_status == TicketStatus.PENDING:
            ticket.first_response_at = datetime.utcnow()
        elif new_status == "resolved":
            ticket.resolved_at = datetime.utcnow()
        elif new_status == "closed":
            ticket.closed_at = datetime.utcnow()
        
        self.db.commit()
        return True, None
    
    def assign_ticket(
        self,
        ticket_id: int,
        agent_id: int
    ) -> Tuple[bool, Optional[str]]:
        ticket = self.get_ticket(ticket_id)
        
        if not ticket:
            return False, "Ticket not found"
        
        ticket.assigned_to = agent_id
        ticket.updated_at = datetime.utcnow()
        
        # Update status if still pending
        if ticket.status == TicketStatus.PENDING:
            ticket.status = TicketStatus.IN_PROGRESS
            ticket.first_response_at = datetime.utcnow()
        
        self.db.commit()
        return True, None
    
    def add_response(
        self,
        ticket_id: int,
        content: str,
        sender_type: str = "agent",
        sender_id: Optional[int] = None,
        sender_name: Optional[str] = None,
        is_internal: bool = False
    ) -> Tuple[Optional[Message], Optional[str]]:
        ticket = self.get_ticket(ticket_id)
        
        if not ticket:
            return None, "Ticket not found"
        
        # Create message
        message = Message(
            message_id=Message.generate_message_id(),
            ticket_id=ticket.ticket_id,
            content=content,
            message_type=MessageType.TEXT,
            sender_type=SenderType(sender_type),
            sender_id=sender_id,
            sender_name=sender_name,
            is_internal=is_internal,
            sent_at=datetime.utcnow()
        )
        
        self.db.add(message)
        
        # Update ticket
        ticket.response_count += 1
        ticket.updated_at = datetime.utcnow()
        
        if sender_type == "agent" and not is_internal:
            if not ticket.first_response_at:
                ticket.first_response_at = datetime.utcnow()
            
            # Auto-update status if pending
            if ticket.status == TicketStatus.PENDING:
                ticket.status = TicketStatus.IN_PROGRESS
        
        self.db.commit()
        self.db.refresh(message)
        
        return message, None
    
    def get_ticket_messages(
        self,
        ticket_id: int,
        include_internal: bool = False
    ) -> List[Message]:
        ticket = self.get_ticket(ticket_id)
        if not ticket:
            return []
        
        query = self.db.query(Message).filter(
            Message.ticket_id == ticket.ticket_id,
            Message.is_deleted == False
        )
        
        if not include_internal:
            query = query.filter(Message.is_internal == False)
        
        return query.order_by(Message.sent_at.asc()).all()
    
    def search_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[int] = None,
        category: Optional[str] = None,
        search_term: Optional[str] = None,
        user_email: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[SupportTicket]:
        query = self.db.query(SupportTicket)
        
        if status:
            query = query.filter(SupportTicket.status == TicketStatus(status))
        
        if priority:
            query = query.filter(SupportTicket.priority == TicketPriority(priority))
        
        if assigned_to:
            query = query.filter(SupportTicket.assigned_to == assigned_to)
        
        if category:
            query = query.filter(SupportTicket.category == category)
        
        if user_email:
            query = query.filter(SupportTicket.email == user_email)
        
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                or_(
                    SupportTicket.subject.ilike(search_pattern),
                    SupportTicket.message.ilike(search_pattern),
                    SupportTicket.ticket_id.ilike(search_pattern)
                )
            )
        
        return query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(limit).all()
    
    def get_user_tickets(self, email: str, limit: int = 20) -> List[SupportTicket]:
        return self.db.query(SupportTicket).filter(
            SupportTicket.email == email
        ).order_by(SupportTicket.created_at.desc()).limit(limit).all()
    
    def get_overdue_tickets(self) -> List[SupportTicket]:
        overdue_tickets = []
        
        pending_tickets = self.db.query(SupportTicket).filter(
            SupportTicket.status == TicketStatus.PENDING,
            SupportTicket.first_response_at.is_(None)
        ).all()
        
        for ticket in pending_tickets:
            sla_hours = self.SLA_RESPONSE_TIME.get(ticket.priority.value, 24)
            sla_deadline = ticket.created_at + timedelta(hours=sla_hours)
            
            if datetime.utcnow() > sla_deadline:
                overdue_tickets.append(ticket)
        
        return overdue_tickets
    
    def get_ticket_statistics(self, days: int = 30) -> Dict:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        tickets = self.db.query(SupportTicket).filter(
            SupportTicket.created_at >= start_date
        ).all()
        
        stats = {
            'total_tickets': len(tickets),
            'by_status': {},
            'by_priority': {},
            'by_category': {},
            'average_response_time_hours': 0,
            'resolution_rate': 0
        }
        
        # Count by status
        for status in TicketStatus:
            count = sum(1 for t in tickets if t.status == status)
            stats['by_status'][status.value] = count
        
        # Count by priority
        for priority in TicketPriority:
            count = sum(1 for t in tickets if t.priority == priority)
            stats['by_priority'][priority.value] = count
        
        # Count by category
        categories = set(t.category for t in tickets if t.category)
        for category in categories:
            count = sum(1 for t in tickets if t.category == category)
            stats['by_category'][category] = count
        
        # Calculate average response time
        response_times = [
            (t.first_response_at - t.created_at).total_seconds() / 3600
            for t in tickets if t.first_response_at
        ]
        if response_times:
            stats['average_response_time_hours'] = round(sum(response_times) / len(response_times), 2)
        
        # Calculate resolution rate
        resolved_count = stats['by_status'].get('resolved', 0) + stats['by_status'].get('closed', 0)
        if stats['total_tickets'] > 0:
            stats['resolution_rate'] = round((resolved_count / stats['total_tickets']) * 100, 2)
        
        return stats
    
    def _auto_detect_priority(self, subject: str, message: str) -> str:
        content = (subject + " " + message).lower()
        
        urgent_keywords = ['urgent', 'critical', 'emergency', 'down', 'not working', 'broken', 'asap']
        high_keywords = ['important', 'soon', 'quickly', 'issue', 'problem', 'error']
        
        if any(keyword in content for keyword in urgent_keywords):
            return 'urgent'
        elif any(keyword in content for keyword in high_keywords):
            return 'high'
        
        return 'medium'
    
    def _auto_categorize(self, subject: str, message: str) -> str:
        """
        Auto-categorize ticket based on content
        
        Args:
            subject: Ticket subject
            message: Ticket message
            
        Returns:
            Category string
        """
        content = (subject + " " + message).lower()
        
        categories = {
            'technical': ['bug', 'error', 'crash', 'not working', 'broken', 'technical', 'code', 'api'],
            'billing': ['billing', 'payment', 'invoice', 'charge', 'subscription', 'refund', 'price'],
            'account': ['account', 'login', 'password', 'access', 'signup', 'registration'],
            'feature_request': ['feature', 'request', 'suggest', 'improvement', 'enhancement', 'add'],
            'general': ['question', 'how to', 'help', 'support', 'inquiry']
        }
        
        for category, keywords in categories.items():
            if any(keyword in content for keyword in keywords):
                return category
        
        return 'general'