from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.referral.services.referral_link import ReferralLinkService
from app.features.referral.schemas.referral_link import (
    GenerateReferralLinkResponse,
    TrackClickRequest,
    TrackClickResponse,
    ClicksBySourceResponse
)
from app.features.auth.routes.auth import get_current_user
from app.platform.db.session import get_db
from app.platform.response import api_response
from app.platform.config import settings

router = APIRouter(prefix="/referral-links", tags=["Referral"])


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a unique referral link"
)
async def generate_referral_link(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a unique referral link for the authenticated user.
    
    Returns:
        GenerateReferralLinkResponse with the referral URL
    """
    service = ReferralLinkService(db)
    referral_url = await service.generate_referral_link(str(current_user.id))
    
    return api_response(
        data={"referralLink": referral_url},
        message="Referral link generated successfully",
        status_code=status.HTTP_201_CREATED
    )


@router.post(
    "/{ref}/click",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Track a referral link click"
)
async def track_referral_click(
    ref: str,
    request_body: TrackClickRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Track a click on a referral link from an external source.
    
    Args:
        ref: The referral code
        request_body: Contains the source (e.g., 'instagram', 'whatsapp')
        request: FastAPI request object for extracting IP and user-agent
        
    Returns:
        TrackClickResponse with success status and landing page URL
    """
    service = ReferralLinkService(db)
    
    # Extract client info
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    
    await service.track_click(
        ref_code=ref,
        source=request_body.source,
        user_agent=user_agent,
        ip_address=ip_address
    )
    
    landing_page_url = settings.LANDING_PAGE_URL.rstrip('/')
    
    return api_response(
        data={
            "status": "success",
            "landingPageUrl": landing_page_url
        },
        message="Click tracked successfully",
        status_code=status.HTTP_200_OK
    )


@router.get(
    "/{ref}/stats",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get referral link statistics"
)
async def get_referral_stats(
    ref: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get click statistics for a referral link.
    
    Args:
        ref: The referral code
        
    Returns:
        ClicksBySourceResponse with total clicks and breakdown by source
    """
    service = ReferralLinkService(db)
    stats = await service.get_stats(ref)
    
    return api_response(
        data=stats,
        message="Referral statistics retrieved successfully",
        status_code=status.HTTP_200_OK
    )
