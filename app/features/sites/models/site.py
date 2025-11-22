from sqlalchemy.orm import relationship
from app.platform.db.base import BaseModel
from sqlalchemy import Column, String, Integer, ForeignKey, Enum, DateTime
import enum

class SiteStatus(enum.Enum):
    active = "active"
    archived = "archived"
    deleted = "deleted"

class Site(BaseModel):
    __tablename__ = "sites"

    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    root_url = Column(String, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    status = Column(Enum(SiteStatus), default=SiteStatus.active, nullable=True)
    total_scans = Column(Integer, default=0, nullable=True)
    last_scanned_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sites")

    def __repr__(self):
        return f"<Site(id={self.id}, root_url={self.root_url}, user_id={self.user_id})>"
