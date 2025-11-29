from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status

from app.features.referral.models.referral_link import ReferralLink, ReferralClick
from app.features.waitlist.utils.referral_code_generator import generate_referral_code
from app.platform.config import settings
from app.platform.logger import get_logger

logger = get_logger(__name__)


class ReferralLinkService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_referral_link(self, user_id: str) -> str:
        """
        Generate a unique referral link for a user.
        Returns the full referral URL.
        """
        # Check if user already has a referral link
        result = await self.db.execute(
            select(ReferralLink).where(ReferralLink.user_id == user_id)
        )
        existing_link = result.unique().scalar_one_or_none()
        
        if existing_link:
            return self._build_referral_url(existing_link.referral_code)
        
        # Generate unique code
        referral_code = generate_referral_code(10)
        while True:
            result = await self.db.execute(
                select(ReferralLink).where(ReferralLink.referral_code == referral_code)
            )
            if not result.unique().scalar_one_or_none():
                break
            referral_code = generate_referral_code(10)
        
        # Create new referral link
        link = ReferralLink(
            user_id=user_id,
            referral_code=referral_code,
            total_clicks=0
        )
        self.db.add(link)
        try:
            await self.db.commit()
        except Exception as exc:
            logger.exception(f"Failed to create referral link for user {user_id}", exc_info=exc)
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate referral link at this time."
            )
        
        return self._build_referral_url(referral_code)
    
    async def track_click(self, ref_code: str, source: str, user_agent: str = None, ip_address: str = None) -> None:
        """
        Track a click on a referral link.
        """
        # Get the referral link
        result = await self.db.execute(
            select(ReferralLink).where(ReferralLink.referral_code == ref_code)
        )
        link = result.unique().scalar_one_or_none()
        
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral link not found"
            )
        
        # Create click record
        click = ReferralClick(
            referral_link_id=link.id,
            source=source,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Increment click count
        link.total_clicks += 1
        
        self.db.add(click)
        try:
            await self.db.commit()
        except Exception as exc:
            logger.exception(f"Failed to track click for referral code {ref_code}", exc_info=exc)
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not track referral click at this time."
            )
    
    async def get_stats(self, ref_code: str) -> dict:
        """
        Get click statistics for a referral link.
        """
        # Get the referral link
        result = await self.db.execute(
            select(ReferralLink)
            .where(ReferralLink.referral_code == ref_code)
            .options(joinedload(ReferralLink.clicks))
        )
        
        link = result.unique().scalar_one_or_none()
        
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral link not found"
            )
        
        # Calculate clicks by source
        clicks_by_source = {}
        for click in link.clicks:
            clicks_by_source[click.source] = clicks_by_source.get(click.source, 0) + 1
        
        return {
            "totalClicks": link.total_clicks,
            "clicksBySource": clicks_by_source
        }
    
    def _build_referral_url(self, referral_code: str) -> str:
        """Build the full referral URL."""
        landing_page = settings.LANDING_PAGE_URL.rstrip('/')
        return f"{landing_page}/landing?ref={referral_code}"
