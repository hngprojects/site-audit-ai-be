import secrets
import json
import logging
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.referral.models.referral import Referral
from app.platform.config import settings

logger = logging.getLogger(__name__)


class ReferralService:
    """Service for managing user referral links."""
    
    REFERRAL_CODE_LENGTH = 12
    LANDING_PAGE_BASE = "https://sitelytics.com"
    
    @staticmethod
    def generate_referral_code() -> str:
        """Generate a unique 12-character referral code."""
        return secrets.token_urlsafe(REFERRAL_SERVICE_CODE_LENGTH)[:ReferralService.REFERRAL_CODE_LENGTH]
    
    @staticmethod
    async def get_or_create_referral(
        user_id: str,
        db: AsyncSession
    ) -> Referral:
        """
        Get existing referral link for user, or create if doesn't exist.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            Referral object with user's unique referral code
        """
        # Check if referral exists
        query = select(Referral).where(Referral.user_id == user_id)
        result = await db.execute(query)
        referral = result.scalar_one_or_none()
        
        if referral:
            return referral
        
        # Create new referral
        referral_code = ReferralService.generate_referral_code()
        
        referral = Referral(
            user_id=user_id,
            referral_code=referral_code,
            share_title="I just scanned my website with Sitelytics",
            landing_page_url=ReferralService.LANDING_PAGE_BASE,
            click_data=json.dumps({})
        )
        
        db.add(referral)
        await db.commit()
        await db.refresh(referral)
        
        logger.info(f"Created referral link for user {user_id}: {referral_code}")
        return referral
    
    @staticmethod
    async def get_referral_by_code(
        referral_code: str,
        db: AsyncSession
    ) -> Optional[Referral]:
        """
        Retrieve referral by code.
        
        Args:
            referral_code: The referral code
            db: Database session
            
        Returns:
            Referral object or None if not found
        """
        query = select(Referral).where(Referral.referral_code == referral_code)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def track_referral_click(
        referral_code: str,
        source: str,
        db: AsyncSession
    ) -> Optional[Referral]:
        """
        Track a click on the referral link.
        
        Args:
            referral_code: The referral code being clicked
            source: Where the click came from (instagram, whatsapp, facebook, twitter, direct, etc.)
            db: Database session
            
        Returns:
            Updated Referral object or None if not found
        """
        referral = await ReferralService.get_referral_by_code(referral_code, db)
        
        if not referral:
            logger.warning(f"Referral code not found: {referral_code}")
            return None
        
        # Increment total clicks
        referral.total_clicks += 1
        referral.last_clicked_at = datetime.utcnow()
        
        # Update click_data JSON
        try:
            click_data = json.loads(referral.click_data or "{}")
        except json.JSONDecodeError:
            click_data = {}
        
        # Normalize source name
        source = source.lower().strip()
        
        # Increment count for this source
        click_data[source] = click_data.get(source, 0) + 1
        referral.click_data = json.dumps(click_data)
        
        await db.commit()
        await db.refresh(referral)
        
        logger.info(f"Tracked click on referral {referral_code} from {source}")
        return referral
    
    @staticmethod
    def build_share_url(referral_code: str) -> str:
        """
        Build the full shareable referral URL.
        
        Args:
            referral_code: The referral code
            
        Returns:
            Full URL like https://sitelytics.com/ref/abc123def456
        """
        return f"{ReferralService.LANDING_PAGE_BASE}/ref/{referral_code}"
    
    @staticmethod
    async def update_referral(
        user_id: str,
        share_title: Optional[str],
        share_description: Optional[str],
        landing_page_url: Optional[str],
        db: AsyncSession
    ) -> Optional[Referral]:
        """
        Update referral link details.
        
        Args:
            user_id: User ID
            share_title: New share title
            share_description: New share description
            landing_page_url: New landing page URL
            db: Database session
            
        Returns:
            Updated Referral object or None if not found
        """
        query = select(Referral).where(Referral.user_id == user_id)
        result = await db.execute(query)
        referral = result.scalar_one_or_none()
        
        if not referral:
            return None
        
        if share_title:
            referral.share_title = share_title
        if share_description:
            referral.share_description = share_description
        if landing_page_url:
            referral.landing_page_url = landing_page_url
        
        await db.commit()
        await db.refresh(referral)
        
        logger.info(f"Updated referral for user {user_id}")
        return referral
