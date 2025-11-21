
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.platform.db.session import get_db
from app.features.support.schemas.support_request import (
    EmailSupportRequest,
    EmailSupportResponse,
    TicketResponse,
    TicketStatusUpdate,
    TicketResponseAdd,
    TicketSearchParams,
    TicketListResponse
)
from services import ValidationService, TicketService, EmailService, NotificationService

router = APIRouter(
    prefix="/api/support/email",
    tags=["Email Support"]
)


@router.post("/", response_model=EmailSupportResponse, status_code=status.HTTP_201_CREATED)
async def create_email_support_ticket(
    request: EmailSupportRequest,
    db: Session = Depends(get_db)
):
    
    # Validate request
    is_valid, errors = ValidationService.validate_support_request(request.dict())
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors}
        )
    
    # Check for spam
    is_spam, spam_reasons = ValidationService.check_spam_indicators(request.dict())
    if is_spam:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Potential spam detected",
                "reasons": spam_reasons
            }
        )
    
    # Sanitize content
    sanitized_message = ValidationService.sanitize_text(request.message)
    sanitized_subject = ValidationService.sanitize_text(request.subject)
    
    # Create ticket
    ticket_service = TicketService(db)
    ticket = ticket_service.create_ticket(
        name=request.name,
        email=request.email,
        subject=sanitized_subject,
        message=sanitized_message,
        phone=request.phone,
        ticket_type="email",
        source="api"
    )
    
    # Send notifications
    try:
        email_service = EmailService()
        notification_service = NotificationService(email_service)
        notification_service.notify_new_ticket(ticket.to_dict())
    except Exception as e:
        # Log error but don't fail the request
        print(f"Failed to send notification: {str(e)}")
    
    return EmailSupportResponse(
        success=True,
        message="Support ticket created successfully. We'll respond within 24 hours.",
        ticket=TicketResponse.from_orm(ticket)
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db)
):

    
    # Validate ticket ID format
    if not ValidationService.validate_ticket_id(ticket_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ticket ID format"
        )
    
    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket_by_ticket_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    return TicketResponse.from_orm(ticket)


@router.patch("/{ticket_id}/status", response_model=dict)
async def update_ticket_status(
    ticket_id: str,
    status_update: TicketStatusUpdate,
    db: Session = Depends(get_db)
):

    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket_by_ticket_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    success, error = ticket_service.update_ticket_status(
        ticket_id=ticket.id,
        new_status=status_update.status,
        agent_id=status_update.agent_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {
        "success": True,
        "message": f"Ticket status updated to {status_update.status}",
        "ticket_id": ticket_id
    }


@router.post("/{ticket_id}/responses", response_model=dict)
async def add_ticket_response(
    ticket_id: str,
    response: TicketResponseAdd,
    db: Session = Depends(get_db)
):
    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket_by_ticket_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    # Sanitize content
    sanitized_content = ValidationService.sanitize_text(response.content)
    
    message, error = ticket_service.add_response(
        ticket_id=ticket.id,
        content=sanitized_content,
        sender_type="agent",
        sender_name=response.sender_name,
        is_internal=response.is_internal
    )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Send notification to user if not internal
    if not response.is_internal:
        try:
            email_service = EmailService()
            notification_service = NotificationService(email_service)
            notification_service.notify_ticket_update(
                ticket.to_dict(),
                sanitized_content
            )
        except Exception as e:
            print(f"Failed to send notification: {str(e)}")
    
    return {
        "success": True,
        "message": "Response added successfully",
        "message_id": message.message_id
    }


@router.get("/{ticket_id}/messages", response_model=List[dict])
async def get_ticket_messages(
    ticket_id: str,
    include_internal: bool = False,
    db: Session = Depends(get_db)
):
    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket_by_ticket_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    messages = ticket_service.get_ticket_messages(
        ticket_id=ticket.id,
        include_internal=include_internal
    )
    
    return [msg.to_dict() for msg in messages]


@router.post("/search", response_model=TicketListResponse)
async def search_tickets(
    search_params: TicketSearchParams,
    db: Session = Depends(get_db)
):

    ticket_service = TicketService(db)
    tickets = ticket_service.search_tickets(
        status=search_params.status,
        priority=search_params.priority,
        category=search_params.category,
        search_term=search_params.search_term,
        user_email=search_params.user_email,
        limit=search_params.limit,
        offset=search_params.offset
    )
    
    return TicketListResponse(
        success=True,
        total=len(tickets),
        tickets=[TicketResponse.from_orm(t) for t in tickets]
    )


@router.get("/user/{email}", response_model=TicketListResponse)
async def get_user_tickets(
    email: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    
    # Validate email
    is_valid, error = ValidationService.validate_email(email)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    ticket_service = TicketService(db)
    tickets = ticket_service.get_user_tickets(email=email, limit=limit)
    
    return TicketListResponse(
        success=True,
        total=len(tickets),
        tickets=[TicketResponse.from_orm(t) for t in tickets]
    )