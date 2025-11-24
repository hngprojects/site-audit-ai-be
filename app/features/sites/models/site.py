from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime, UniqueConstraint, Index, Boolean
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


class Site(BaseModel):
    """
    Unified site model for both authenticated portfolio management and global scan cache.
    
    Usage:
    - Auth users: user_id is set, they can manage this site in their portfolio
    - Unauth scans: user_id is NULL, site exists only as scan cache entry
    - Claiming: When unauth user registers, their scans can be "claimed" by setting user_id
    """
    __tablename__ = "sites"

    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True) 
    root_url = Column(String, index=True, nullable=False)  # Multiple users can have same site in portfolios, nless mark wants us to make it unique per user
    display_name = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    status = Column(Enum(SiteStatus), default=SiteStatus.active, nullable=True)
    
    # Scan tracking (updated by both auth and unauth scans)
    total_scans = Column(Integer, default=0, nullable=False)
    last_scanned_at = Column(DateTime, nullable=True)
    
    # Portfolio management flags (only for auth users)
    is_portfolio_site = Column(Boolean, default=False, nullable=False)  # True = user actively managing this site

    user = relationship("User", back_populates="sites")

    __table_args__ = (
        UniqueConstraint("user_id", "root_url", name="uq_user_site_root_url"),
        
        Index("ix_sites_root_url_last_scanned", "root_url", "last_scanned_at"),
        Index("ix_sites_cache_entry", "root_url", postgresql_where="user_id IS NULL", unique=True),
    )
