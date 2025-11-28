from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from datetime import datetime

from app.platform.db.base import BaseModel


class Referral(BaseModel):
    """
    User referral links for sharing scan results.
    
    Each user gets a unique referral code that links to the landing page
    and tracks clicks for referral analytics.
    """
    __tablename__ = "referrals"
    
    # User who owns this referral link
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Unique referral code (short, shareable)
    referral_code = Column(String(12), unique=True, nullable=False, index=True)
    
    # Share message customization
    share_title = Column(String(255), default="I just scanned my website with Sitelytics", nullable=False)
    share_description = Column(String(512), nullable=True)
    
    # Click tracking
    total_clicks = Column(Integer, default=0, nullable=False)
    click_data = Column(String, default="{}") # JSON string for click sources: {"instagram": 5, "whatsapp": 3, ...}
    
    # Landing page URL (can be customized per user in future)
    landing_page_url = Column(String(512), default="https://sitelytics.com", nullable=False)
    
    # Timestamps (created_at and updated_at inherited from BaseModel)
    last_clicked_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_referral"),  # One referral per user
        Index("idx_referrals_code", "referral_code"),
    )
