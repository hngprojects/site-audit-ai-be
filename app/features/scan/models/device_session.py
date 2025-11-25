from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from datetime import datetime, date

from app.platform.db.base import BaseModel


class DeviceSession(BaseModel):
    """
    Anonymous device tracking for rate limiting.
    """
    __tablename__ = "device_sessions"
    
    # Device identification (SHA256 hash of raw device_id)
    device_hash = Column(String(64), nullable=True, unique=True, index=True)
    
    # Associated user (if migrated)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Rate limiting
    daily_scan_count = Column(Integer, default=0, nullable=False)
    quota_remaining = Column(Integer, default=30, nullable=False)
    last_scan_date = Column(DateTime, nullable=True)
    
    # Device metadata (for analytics)
    user_agent = Column(String(512), nullable=True)
    platform = Column(String(50), nullable=True)  # 'ios', 'android', 'web'
    
    # Statistics
    total_scans = Column(Integer, default=0, nullable=False)
    
    # Timestamps (created_at and updated_at inherited from BaseModel)
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Constraints
    __table_args__ = (
        Index('idx_device_sessions_user', 'user_id'),
    )
