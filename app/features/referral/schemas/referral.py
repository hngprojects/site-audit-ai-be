from typing import Optional, Dict
from pydantic import BaseModel
from datetime import datetime


class ReferralLinkResponse(BaseModel):
    """Response with shareable referral link."""
    referral_code: str
    share_url: str
    share_title: str
    share_description: Optional[str]
    total_clicks: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "referral_code": "abc123def456",
                "share_url": "https://sitelytics.com/ref/abc123def456",
                "share_title": "I just scanned my website with Sitelytics",
                "share_description": "Get a free audit of your website's health, SEO, and performance.",
                "total_clicks": 42
            }
        }


class ReferralAnalyticsResponse(BaseModel):
    """Response with referral click analytics."""
    referral_code: str
    total_clicks: int
    click_sources: Dict[str, int]  # {"instagram": 5, "whatsapp": 3, ...}
    last_clicked_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "referral_code": "abc123def456",
                "total_clicks": 42,
                "click_sources": {
                    "instagram": 15,
                    "whatsapp": 12,
                    "facebook": 8,
                    "twitter": 7,
                    "direct": 0
                },
                "last_clicked_at": "2025-01-15T10:30:00Z",
                "created_at": "2025-01-01T08:00:00Z"
            }
        }


class UpdateReferralRequest(BaseModel):
    """Request to update referral link details."""
    share_title: Optional[str] = None
    share_description: Optional[str] = None
    landing_page_url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "share_title": "I just audited my website with Sitelytics - No coding required!",
                "share_description": "Get insights on SEO, performance, and accessibility.",
                "landing_page_url": "https://sitelytics.com"
            }
        }
