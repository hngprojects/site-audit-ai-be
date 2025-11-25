import re, os
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.platform.services.email import send_email
from jinja2 import Environment, FileSystemLoader
from app.platform.config import settings
from pathlib import Path


from app.features.support.models.support_ticket import (
    SupportTicket, 
    TicketPriority, 
    TicketStatus, 
    TicketCategory
)


PRIORITY_KEYWORDS = {
    TicketPriority.URGENT: {"urgent", "critical", "emergency", "down"},
    TicketPriority.HIGH: {"important", "soon", "issue", "problem"},
}

CATEGORY_KEYWORDS = {
    TicketCategory.TECHNICAL: {"bug", "error", "crash", "broken"},
    TicketCategory.BILLING: {"billing", "payment", "invoice"},
    TicketCategory.ACCOUNT: {"account", "login", "password"},
}

def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b\w+\b", text.lower()))


class TicketService:
    """Ticket management service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _auto_detect_priority(self, subject: str, message: str) -> TicketPriority:
        words = _tokenize(f"{subject} {message}")
        for level in (TicketPriority.URGENT, TicketPriority.HIGH):
            if words & PRIORITY_KEYWORDS[level]:
                return level
        return TicketPriority.MEDIUM

    def _auto_categorize(self, subject: str, message: str) -> TicketCategory:
        words = _tokenize(f"{subject} {message}")
        for category, keywords in CATEGORY_KEYWORDS.items():
            if words & keywords:
                return category
        return TicketCategory.GENERAL


    async def create_ticket(
        self,
        email: str,
        subject: str,
        message: str,
        full_name: str | None = None,
        phone_number: str | None = None,
    ) -> SupportTicket:
        """Create a new support ticket"""

        for _ in range(2):  # one retry if unique ticket_id collides
            ticket = SupportTicket(
                 email=email,
                full_name=full_name,
                phone_number=phone_number,
                subject=subject,
                message=message,
                priority=self._auto_detect_priority(subject, message),
                status=TicketStatus.PENDING,
                category=self._auto_categorize(subject, message),
            )
            self.db.add(ticket)
            
            try:
                await self.db.commit()
                await self.db.refresh(ticket)
                return ticket
            except IntegrityError:
                await self.db.rollback()

        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Could not create ticket after retry"
        )
    

    async def get_ticket_by_id(self, ticket_id: str) -> SupportTicket | None:
        """Get ticket by ticket ID"""
        result = await self.db.execute(
            select(SupportTicket).where(SupportTicket.ticket_id == ticket_id)
        )
        return result.scalar_one_or_none()
    

    async def update_status(self, ticket_id: str, new_status_value: str) -> SupportTicket:
        """Update ticket status"""
        try:
            status_enum = TicketStatus(new_status_value)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid ticket status")

        stmt = (
            update(SupportTicket)
            .where(SupportTicket.ticket_id == ticket_id)
            .values(status=status_enum)
            .returning(SupportTicket)
        )

        result = await self.db.execute(stmt)
        ticket = result.scalars().first()
        
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

        await self.db.commit()
        return ticket
    

    @staticmethod
    async def send_ticket_notification(ticket) -> None:
        template_dir = Path(__file__).resolve().parent.parent / "template"
        template = Environment(loader=FileSystemLoader(str(template_dir))).get_template("admin_email.html")
        html_content = template.render(ticket=ticket)  


        to_email = settings.MAIL_ADMIN_EMAIL
        print(settings.MAIL_ADMIN_EMAIL)
        send_email(to_email, f"New Ticket for {ticket.ticket_id}", html_content)

