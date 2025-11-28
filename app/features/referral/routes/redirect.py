from fastapi import APIRouter, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.features.referral.services.referral_service import ReferralService
from app.platform.db.session import get_db
from app.platform.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["referral-redirect"])


@router.get("/ref/{referral_code}")
async def redirect_referral(
    referral_code: str,
    source: str = Query(default="direct", description="Click source: instagram, whatsapp, facebook, twitter, etc."),
    db: AsyncSession = Depends(get_db)
):
    """
    Redirect endpoint for referral links.
    
    This endpoint:
    1. Tracks the click (increments counter and records source)
    2. Redirects to the landing page
    
    Query Parameters:
        - source: Where the click came from (instagram, whatsapp, etc.) - default: "direct"
    
    Example:
        - GET /ref/abc123def456?source=instagram
        - GET /ref/abc123def456?source=whatsapp
        
    Returns:
        301 redirect to landing page
    """
    try:
        # Track the click
        referral = await ReferralService.track_referral_click(
            referral_code=referral_code,
            source=source,
            db=db
        )
        
        if not referral:
            # If referral not found, still redirect to landing page
            logger.warning(f"Referral code not found: {referral_code}")
            landing_url = settings.LANDING_PAGE_URL or "https://sitelytics.com"
            return RedirectResponse(url=landing_url, status_code=301)
        
        # Redirect to the landing page configured for this referral
        return RedirectResponse(url=referral.landing_page_url, status_code=301)
        
    except Exception as e:
        logger.error(f"Error processing referral redirect for {referral_code}: {e}")
        # Fallback redirect to main landing page
        landing_url = settings.LANDING_PAGE_URL or "https://sitelytics.com"
        return RedirectResponse(url=landing_url, status_code=301)
