
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.platform.db.session import get_db
from app.features.support.schemas.support_request import MessageRequest, MessageResponse
from app.features.support.services import ValidationService, TicketService, EmailService, NotificationService

router = APIRouter(
    prefix="/api/support/message",
    tags=["Message"]
)


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    request: MessageRequest,
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
    is_spam, spam_reasons = ValidationService.check_spam_indicators({
        'message': request.message,
        'subject': ''  # No subject for general messages
    })
    
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
    
    # Create ticket with "message" type
    ticket_service = TicketService(db)
    ticket = ticket_service.create_ticket(
        name=request.name,
        email=request.email,
        subject="General Inquiry",  # Default subject for messages
        message=sanitized_message,
        ticket_type="message",
        priority="medium",
        source="api"
    )
    
    # Send confirmation email
    try:
        email_service = EmailService()
        notification_service = NotificationService(email_service)
        
        # Send message confirmation
        email_service.send_message_confirmation({
            'name': request.name,
            'email': request.email,
            'message': sanitized_message
        })
        
        # Notify support team
        email_service.notify_support_team(ticket.to_dict())
    
    except Exception as e:
        # Log error but don't fail the request
        print(f"Failed to send notification: {str(e)}")
    
    return MessageResponse(
        success=True,
        message="Message sent successfully. We'll get back to you within 24 hours."
    )


@router.get("/status")
async def get_message_status():
    return {
        "service": "Message Submission",
        "status": "operational",
        "expected_response_time": "24 hours",
        "available": True
    }