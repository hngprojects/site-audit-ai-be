from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.support.schemas.contact_us import ContactUsIn, ContactUsResponse
from app.features.support.services.email_service import TicketService
from app.platform.db.session import get_db

router = APIRouter(prefix="support/contact", tags=["contact"])


@router.post("/", response_model=ContactUsResponse, status_code=status.HTTP_201_CREATED)
async def contact_us(
    background_tasks: BackgroundTasks, request: ContactUsIn, db: AsyncSession = Depends(get_db)
):
    """
    Simple contact form - creates a support ticket internally
    - **full_name**: Contact's full name
    - **phone_number**: Contact phone number
    - **email**: Contact email address
    - **message**: Message content
    """
    ticket_service = TicketService(db)
    ticket = await ticket_service.create_ticket(
        email=request.email,
        full_name=request.full_name,
        phone_number=request.phone_number,
        subject="Contact Us Inquiry",  # Generic subject
        message=request.message,
        source="contact_form",
    )

    background_tasks.add_task(TicketService.send_ticket_notification, ticket)
    return {
        "message": "Thank you for contacting us. We'll get back to you soon.",
        "data": {"ticket_id": ticket.ticket_id},
        "status_code": status.HTTP_201_CREATED,
    }
