
import re
import os
from typing import Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.features.support.models.support_ticket import SupportTicket, TicketStatus, TicketPriority


class ValidationService:
    """Validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"
        return True, None
    
    @staticmethod
    def check_spam(message: str, subject: str) -> Tuple[bool, list]:
        """Check for spam indicators"""
        spam_keywords = ['viagra', 'casino', 'lottery', 'click here', 'act now']
        spam_reasons = []
        
        content = (message + subject).lower()
        for keyword in spam_keywords:
            if keyword in content:
                spam_reasons.append(f"Spam keyword: {keyword}")
        
        return len(spam_reasons) > 0, spam_reasons


class TicketService:
    """Ticket management service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_ticket(
        self,
        name: str,
        email: str,
        subject: str,
        message: str,
        phone: Optional[str] = None
    ) -> SupportTicket:
        """Create a new support ticket"""
        
        # Auto-detect priority
        priority = self._auto_detect_priority(subject, message)
        
        ticket = SupportTicket(
            ticket_id=SupportTicket.generate_ticket_id(),
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
            priority=TicketPriority(priority),
            status=TicketStatus.PENDING,
            category=self._auto_categorize(subject, message),
            source="api"
        )
        
        self.db.add(ticket)
        await self.db.commit()
        await self.db.refresh(ticket)
        
        return ticket
    
    async def get_ticket_by_id(self, ticket_id: str) -> Optional[SupportTicket]:
        """Get ticket by ticket ID"""
        result = await self.db.execute(
            select(SupportTicket).where(SupportTicket.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()
    
    async def update_status(self, ticket_id: int, status: str) -> bool:
        """Update ticket status"""
        result = await self.db.execute(
            select(SupportTicket).where(SupportTicket.id == ticket_id)
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            return False
        
        ticket.status = TicketStatus(status)
        ticket.updated_at = datetime.utcnow()
        
        if status == "resolved":
            ticket.resolved_at = datetime.utcnow()
        
        await self.db.commit()
        return True
    
    def _auto_detect_priority(self, subject: str, message: str) -> str:
        """Auto-detect priority based on content"""
        content = (subject + " " + message).lower()
        
        if any(word in content for word in ['urgent', 'critical', 'emergency', 'down']):
            return 'urgent'
        elif any(word in content for word in ['important', 'soon', 'issue', 'problem']):
            return 'high'
        
        return 'medium'
    
    def _auto_categorize(self, subject: str, message: str) -> str:
        """Auto-categorize ticket"""
        content = (subject + " " + message).lower()
        
        if any(word in content for word in ['bug', 'error', 'crash', 'broken']):
            return 'technical'
        elif any(word in content for word in ['billing', 'payment', 'invoice']):
            return 'billing'
        elif any(word in content for word in ['account', 'login', 'password']):
            return 'account'
        
        return 'general'


class EmailService:
    """Email notification service"""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.admin_email = os.getenv('ADMIN_EMAIL', 'admin@tokugawa.emerj.net')
    
    async def send_ticket_notification(self, ticket: SupportTicket) -> bool:
        """Send email notification to admin"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = self.admin_email
            msg['Subject'] = f"New Support Ticket: {ticket.ticket_id}"
            
            body = f"""
            New Support Ticket Received
            
            Ticket ID: {ticket.ticket_id}
            From: {ticket.name} ({ticket.email})
            Subject: {ticket.subject}
            Priority: {ticket.priority.value}
            
            Message:
            {ticket.message}
            
            ---
            Tokugawa Support System
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False