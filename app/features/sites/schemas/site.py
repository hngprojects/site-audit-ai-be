from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.features.sites.models.site import SiteStatus, ScanFrequency


class SiteBase(BaseModel):
    root_url: str
    display_name: Optional[str] = None
    favicon_url: Optional[str] = None
    status: Optional[SiteStatus] = SiteStatus.active


class SiteCreate(BaseModel):
    root_url: str
    display_name: Optional[str] = None
    favicon_url: Optional[str] = None
    status: Optional[SiteStatus] = SiteStatus.active


class SiteUpdate(BaseModel):
    display_name: Optional[str] = None
    favicon_url: Optional[str] = None
    status: Optional[SiteStatus] = None


class SitePeriodicScanUpdate(BaseModel):
    """Schema for updating periodic scan settings"""
    scan_frequency: ScanFrequency
    scan_frequency_enabled: bool


class SiteResponse(SiteBase):
    id: str
    total_scans: int
    last_scanned_at: Optional[datetime]
    scan_frequency: ScanFrequency
    scan_frequency_enabled: bool
    next_scheduled_scan: Optional[datetime]
    last_periodic_scan_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
