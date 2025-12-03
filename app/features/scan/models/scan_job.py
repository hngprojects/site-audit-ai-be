from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Index, CheckConstraint, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.platform.db.base import BaseModel


class ScanJobStatus(enum.Enum):
    """Scan job status state machine"""
    queued = "queued"
    discovering = "discovering"
    selecting = "selecting"
    scraping = "scraping"
    analyzing = "analyzing"
    aggregating = "aggregating"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ScanJob(BaseModel):
  
    __tablename__ = "scan_jobs"
    
    # Foreign Keys (Please, exactly one of user_id OR device_id must be set)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # device_id = Column(String, ForeignKey("device_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    device_id = Column(String, nullable=True, index=True)  # TODO: Add FK to device_sessions when device tracking is implemented

    site_id = Column(String, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)  # Every scan must be linked to a site
    
    # Relationship to access site data (root_url, domain, etc.)
    site = relationship("Site", foreign_keys=[site_id])
    
    # Job status (state machine)
    status = Column(Enum(ScanJobStatus), default=ScanJobStatus.queued, nullable=False, index=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Discovery phase results
    pages_discovered = Column(Integer, nullable=True)
    
    # LLM Selection phase (LLM Call #1)
    pages_selected = Column(Integer, nullable=True)
    
    # Scraping phase
    pages_scanned = Column(Integer, nullable=True)
    
    # Optimization metrics
    pages_llm_analyzed = Column(Integer, default=0)
    pages_cache_hit = Column(Integer, default=0)  # Pages served from cache
    
    # Aggregated scores
    score_overall = Column(Integer, nullable=True)  # 0-100
    score_seo = Column(Integer, nullable=True)
    score_accessibility = Column(Integer, nullable=True)
    score_performance = Column(Integer, nullable=True)
    
    # Issue counts (denormalized)
    total_issues = Column(Integer, default=0, nullable=False)
    critical_issues_count = Column(Integer, default=0, nullable=False)
    warning_issues_count = Column(Integer, default=0, nullable=False)
    
    worker_id = Column(String(255), nullable=True)
    celery_task_id = Column(String(128), nullable=True, index=True)
    
    # Timestamps (created_at and updated_at inherited from BaseModel)
    queued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            '(user_id IS NOT NULL AND device_id IS NULL) OR (user_id IS NULL AND device_id IS NOT NULL)',
            name='check_owner_exclusivity'
        ),
        Index('idx_scan_jobs_status', 'status'),
        Index('idx_scan_jobs_user_site', 'site_id', postgresql_where=Column('site_id').isnot(None)),
    )
