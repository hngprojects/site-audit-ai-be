from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime, UniqueConstraint, Index, Boolean, CheckConstraint
from sqlalchemy.orm import relationship
from app.platform.db.base import BaseModel
import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.platform.db.base import BaseModel


class SiteStatus(enum.Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"


class ScanFrequency(enum.Enum):
    """Periodic scan frequency options"""
    disabled = "disabled"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class Site(BaseModel):
    """
    Site model with flexible ownership — user_id takes priority over device_id.

    Ownership resolution (in order):
    1. If user_id is set → site belongs to that user (authenticated ownership)
    2. Else if device_id is set → site belongs to that device (anonymous ownership)
    3. If both NULL → invalid (blocked by constraint)

    This enables:
    - Anonymous users create sites with device_id
    - When they sign up → we set user_id (device_id stays as history)
    - All future operations use user_id
    - No data loss during "claim" flow
    """
    __tablename__ = "sites"

    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True) 
    device_id = Column(String, index=True, nullable=True)  # Can coexist with user_id
    root_url = Column(String, index=True, nullable=False)  # Multiple users can have same site in portfolios, nless mark wants us to make it unique per user
    display_name = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    status = Column(Enum(SiteStatus), default=SiteStatus.active, nullable=True)
    
    # Scan tracking (updated by both auth and unauth scans)
    total_scans = Column(Integer, default=0, nullable=False)
    last_scanned_at = Column(DateTime, nullable=True)
    
    # Portfolio management flags (only for auth users)
    is_portfolio_site = Column(Boolean, default=False, nullable=False)  # True = user actively managing this site

    # Periodic scanning settings
    scan_frequency = Column(Enum(ScanFrequency), default=ScanFrequency.disabled, nullable=False)
    scan_frequency_enabled = Column(Boolean, default=False, nullable=False)  # Quick toggle on/off
    next_scheduled_scan = Column(DateTime, nullable=True)  # When the next periodic scan should run
    last_periodic_scan_at = Column(DateTime, nullable=True)  # Last time a periodic scan was triggered

    user = relationship("User", back_populates="sites")

    __table_args__ = (
        UniqueConstraint("user_id", "root_url", name="uq_user_site_root_url"),  # One site per user (if they have one)
        UniqueConstraint("device_id", "root_url", name="uq_device_site_root_url"),  # One site per device (only matters when no user_id)
        
        CheckConstraint("user_id IS NOT NULL OR device_id IS NOT NULL", name="ck_site_has_owner"),  # At least one owner must exist

        Index("ix_sites_root_url_last_scanned", "root_url", "last_scanned_at"),
    )