from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.support.schemas.contact_us import ContactUsRequest
from app.features.support.services.email_service import TicketService
from app.features.support.services.webhook import send_contact_webhook
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/support", tags=["Contact"])


@router.post("/contact-us", status_code=status.HTTP_201_CREATED)
async def contact_us(
    background_tasks: BackgroundTasks, request: ContactUsRequest, db: AsyncSession = Depends(get_db)
):
    """
    Contact us form submission
    - Creates a support ticket in the database
    - Sends data to webhook
    - Sends email notification to admin
    """

    ticket_service = TicketService(db)
    ticket = await ticket_service.create_ticket(
        email=request.email,
        full_name=request.full_name,
        phone_number=request.phone_number,
        subject=f"Contact Form: {request.message[:50]}...",
        message=request.message,
        source="web" if request.page else "mobile",
    )

    submitted_at = datetime.now(timezone.utc).isoformat()
    background_tasks.add_task(
        send_contact_webhook,
        name=request.full_name,
        email=request.email,
        message=request.message,
        user_id=ticket.ticket_id,  # Using ticket_id as userId
        submitted_at=submitted_at,
        category=ticket.category.value,
        priority=ticket.priority.value,
        page=request.page,
    )

    background_tasks.add_task(TicketService.send_ticket_notification, ticket)

    return api_response(
        message="Thank you for contacting us. We'll get back to you soon!",
        data={
            "ticket_id": ticket.ticket_id,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "category": ticket.category.value,
        },
        status_code=status.HTTP_201_CREATED,
    )
