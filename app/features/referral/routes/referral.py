from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.features.referral.schemas.referral import (
    ReferralLinkResponse,
    ReferralAnalyticsResponse,
    UpdateReferralRequest
)
from app.features.referral.services.referral_service import ReferralService
from app.features.auth.routes.auth import get_current_user
from app.platform.response import api_response
from app.platform.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/referral", tags=["referral"])


@router.post("/link", response_model=ReferralLinkResponse)
async def get_share_link(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get or create a unique referral/share link for the authenticated user.
    
    This link can be shared on social media (Instagram, WhatsApp, etc.) with a
    scan result image. The link will:
    - Always point to the landing page
    - Track clicks and their sources
    - Attribute new users back to the referrer
    
    Returns:
        ReferralLinkResponse with shareable URL and current click count
    """
    try:
        # Get or create referral for this user
        referral = await ReferralService.get_or_create_referral(
            user_id=current_user.id,
            db=db
        )
        
        share_url = ReferralService.build_share_url(referral.referral_code)
        
        return api_response(
            data={
                "referral_code": referral.referral_code,
                "share_url": share_url,
                "share_title": referral.share_title,
                "share_description": referral.share_description,
                "total_clicks": referral.total_clicks
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting referral link for user {current_user.id}: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error generating referral link: {str(e)}",
            data={}
        )


@router.get("/analytics", response_model=ReferralAnalyticsResponse)
async def get_referral_analytics(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics for the user's referral link.
    
    Shows:
    - Total number of clicks
    - Clicks breakdown by source (Instagram, WhatsApp, Facebook, etc.)
    - Last click timestamp
    
    Returns:
        ReferralAnalyticsResponse with click analytics
    """
    try:
        referral = await ReferralService.get_or_create_referral(
            user_id=current_user.id,
            db=db
        )
        
        import json
        click_sources = json.loads(referral.click_data or "{}")
        
        return api_response(
            data={
                "referral_code": referral.referral_code,
                "total_clicks": referral.total_clicks,
                "click_sources": click_sources,
                "last_clicked_at": referral.last_clicked_at,
                "created_at": referral.created_at
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting referral analytics for user {current_user.id}: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching analytics: {str(e)}",
            data={}
        )


@router.put("/link", response_model=ReferralLinkResponse)
async def update_share_link(
    data: UpdateReferralRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update referral link details (title, description, landing page URL).
    
    Args:
        data: UpdateReferralRequest with new details
        
    Returns:
        Updated ReferralLinkResponse
    """
    try:
        referral = await ReferralService.update_referral(
            user_id=current_user.id,
            share_title=data.share_title,
            share_description=data.share_description,
            landing_page_url=data.landing_page_url,
            db=db
        )
        
        if not referral:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Referral link not found",
                data={}
            )
        
        share_url = ReferralService.build_share_url(referral.referral_code)
        
        return api_response(
            data={
                "referral_code": referral.referral_code,
                "share_url": share_url,
                "share_title": referral.share_title,
                "share_description": referral.share_description,
                "total_clicks": referral.total_clicks
            }
        )
        
    except Exception as e:
        logger.error(f"Error updating referral link for user {current_user.id}: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error updating referral link: {str(e)}",
            data={}
        )
