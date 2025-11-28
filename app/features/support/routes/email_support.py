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

    return api_response(
        data=TicketResponse.model_validate(updated_ticket),
        message="Ticket status updated successfully",
        status_code=status.HTTP_200_OK,
    )
