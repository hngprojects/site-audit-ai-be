from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.support.schemas.support_request import (
    EmailSupportRequest,
    TicketResponse,
    TicketStatusUpdate,
    ValidationService,
)
from app.features.support.services.email_service import EmailService, TicketService
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/support/email", tags=["Email Support"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(request: EmailSupportRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new email support ticket
    - **email**: User's email address
    - **subject**: Support request subject
    - **message**: Detailed message
    """

    # Validate email
    is_valid, error = ValidationService.validate_email(request.email)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)

    # Check spam
    is_spam, reasons = ValidationService.check_spam(request.message, request.subject)
    if is_spam:
        raise HTTPException(status_code=400, detail={"error": "Spam detected", "reasons": reasons})

    # Create ticket
    ticket_service = TicketService(db)
    ticket = await ticket_service.create_ticket(
        # name=request.name,
        email=request.email,
        subject=request.subject,
        message=request.message,
        # phone=request.phone
    )

    # Send email notification (async in background)
    try:
        email_service = EmailService()
        await email_service.send_ticket_notification(ticket)
    except Exception as e:
        print(f"Email notification failed: {e}")

    return api_response(
        message="Support ticket created successfully", data=TicketResponse.model_validate(ticket)
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    """Get ticket details by ticket ID"""

    ticket_service = TicketService(db)
    ticket = await ticket_service.get_ticket_by_id(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return api_response(data=TicketResponse.model_validate(ticket))


@router.patch("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str, status_update: TicketStatusUpdate, db: AsyncSession = Depends(get_db)
):
    """Update ticket status"""

    ticket_service = TicketService(db)
    ticket = await ticket_service.get_ticket_by_id(ticket_id)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    success = await ticket_service.update_status(ticket.id, status_update.status)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to update status")

    return api_response(data=ticket_id)
