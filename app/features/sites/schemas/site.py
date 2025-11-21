from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from app.features.sites.models.site import SiteStatus

class SiteBase(BaseModel):
    root_url: HttpUrl
    display_name: Optional[str] = None
    favicon_url: Optional[HttpUrl] = None
    status: Optional[SiteStatus] = SiteStatus.active

class SiteCreate(BaseModel):
    root_url: HttpUrl
    display_name: Optional[str] = None
    favicon_url: Optional[HttpUrl] = None
    status: Optional[SiteStatus] = SiteStatus.active

class SiteUpdate(BaseModel):
    display_name: Optional[str] = None
    favicon_url: Optional[HttpUrl] = None
    status: Optional[SiteStatus] = None

class SiteResponse(SiteBase):
    id: str
    total_scans: int
    last_scanned_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True