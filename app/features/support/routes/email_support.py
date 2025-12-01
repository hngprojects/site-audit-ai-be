from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.support.schemas.support_request import (
    EmailSupportRequest,
    TicketResponse,
    TicketStatusUpdate,
)
from app.features.support.services.email_service import TicketService
from app.platform.db.session import get_db
from app.platform.response import api_response

from app.platform.services.email import send_email
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status


router = APIRouter(prefix="/support/email", tags=["Email Support"])


@router.post("/",  status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
        background_tasks: BackgroundTasks,
        request: EmailSupportRequest, 
        db: AsyncSession = Depends(get_db)
    ):
    """
    Create a new email support ticket
    - **email**: User's email address
    - **subject**: Support request subject
    - **message**: Detailed message
    """
    # Create ticket
    ticket_service = TicketService(db)
    ticket = await ticket_service.create_ticket(
        email=request.email,
        message=request.message,
        subject=request.subject,
        full_name=request.full_name,
        phone_number=request.phone_number,
        source=request.source,
    )

    background_tasks.add_task(TicketService.send_ticket_notification, ticket)

    # NEW: Send notification to user (if authenticated)
    if hasattr(ticket, 'user_id') and ticket.user_id:
        from app.features.notifications.services.notifications import NotificationService
        from app.features.notifications.models.notifications import NotificationType, NotificationPriority
        
        notification_service = NotificationService(db)
        await notification_service.create_notification(
            user_id=str(ticket.user_id),
            title="Support Ticket Created",
            message=f"We received your support request: {request.subject}. Our team will respond soon.",
            notification_type=NotificationType.SUPPORT_RESPONSE,
            priority=NotificationPriority.MEDIUM,
            action_url=f"/support/tickets/{ticket.id}"
        )
   
    return api_response(
        message="Support ticket created successfully", 
        data=TicketResponse.model_validate(ticket),
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/{ticket_id}")
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Get ticket details by ticket ID"""

    ticket_service = TicketService(db)
    ticket = await ticket_service.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    return api_response(data=TicketResponse.model_validate(ticket))


@router.patch("/{ticket_id}", status_code=status.HTTP_200_OK)
async def update_ticket_status(
    ticket_id: str, 
    status_update: TicketStatusUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """Update ticket status"""
    ticket_service = TicketService(db)
    updated_ticket = await ticket_service.update_status(
        ticket_id, 
        status_update.status
    )

    # NEW: Notify user of status change
    if hasattr(updated_ticket, 'user_id') and updated_ticket.user_id:
        from app.features.notifications.services.notifications import NotificationService
        from app.features.notifications.models.notifications import NotificationType, NotificationPriority
        
        status_messages = {
            "IN_PROGRESS": "Your support ticket is being reviewed by our team",
            "RESOLVED": "Your support ticket has been resolved! Check the ticket for details.",
            "CLOSED": "Your support ticket has been closed"
        }
        
        message = status_messages.get(
            status_update.status, 
            f"Your ticket status changed to {status_update.status}"
        )
        
        notification_service = NotificationService(db)
        await notification_service.create_notification(
            user_id=str(updated_ticket.user_id),
            title="Support Ticket Updated",
            message=message,
            notification_type=NotificationType.SUPPORT_RESPONSE,
            priority=NotificationPriority.MEDIUM,
            action_url=f"/support/tickets/{ticket_id}"
        )

    return api_response(
        data=TicketResponse.model_validate(updated_ticket),
        message="Ticket status updated successfully",
        status_code=status.HTTP_200_OK,
    )
