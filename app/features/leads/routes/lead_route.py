from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.leads.schemas.lead_schema import LeadCreate, LeadOut
from app.features.leads.services.lead_service import LeadService
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/leads", tags=["Leads"])

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    service = LeadService(db)
    lead = await service.create_lead(
        email=payload.email
    )

    # Reuse TicketService-like pattern: send emails in background
    background_tasks.add_task(LeadService.send_lead_confirmation, lead)
    background_tasks.add_task(LeadService.send_admin_notification, lead)

    return api_response(
        message="Thanks! We received your request and will get back to you.",
        data=LeadOut.model_validate(lead),
        status_code=status.HTTP_201_CREATED,
    )
