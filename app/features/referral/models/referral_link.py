from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func as sql_func
from datetime import datetime

from app.platform.db.base import BaseModel


class ReferralLink(BaseModel):
    __tablename__ = "referral_links"
    
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    referral_code = Column(String(10), unique=True, nullable=False, index=True)
    total_clicks = Column(Integer, default=0)
    
    user = relationship("User", back_populates="referral_links")
    clicks = relationship("ReferralClick", back_populates="referral_link", cascade="all, delete-orphan")


class ReferralClick(BaseModel):
    __tablename__ = "referral_clicks"
    
    referral_link_id = Column(String(36), ForeignKey("referral_links.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False)  # instagram, whatsapp, twitter, etc.
    clicked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    
    referral_link = relationship("ReferralLink", back_populates="clicks")