from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, Text, ForeignKey, Index, JSON
from datetime import datetime

from app.platform.db.base import BaseModel


class ScanPage(BaseModel):
    """
    Individual page results within a scan job.
    
    Stores per-page metrics, scores, and cache optimization data.
    """
    __tablename__ = "scan_pages"
    
    # Foreign Key
    scan_job_id = Column(String, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Page identification
    page_url = Column(String(2048), nullable=False)
    page_url_normalized = Column(String(2048), nullable=False, index=True)
    page_title = Column(String(512), nullable=True)
    
    # Cache key (SHA256 of canonicalized HTML)
    page_hash = Column(String(64), nullable=True, index=True)
    
    # HTTP metadata
    http_status = Column(Integer, nullable=True)
    content_type = Column(String(255), nullable=True)
    content_length_bytes = Column(Integer, nullable=True)
    
    # Performance metrics
    load_time_ms = Column(Integer, nullable=True)
    ttfb_ms = Column(Integer, nullable=True)  # Time to First Byte
    
    # Scores per page
    score_overall = Column(Integer, nullable=True)  # 0-100
    score_seo = Column(Integer, nullable=True)
    score_accessibility = Column(Integer, nullable=True)
    score_performance = Column(Integer, nullable=True)
    
    # Detailed LLM analysis results (structured JSON from Gemini)
    analysis_details = Column(JSON, nullable=True)
    
    # Issue counts (aggregated)
    critical_issues_count = Column(Integer, default=0, nullable=False)
    warning_issues_count = Column(Integer, default=0, nullable=False)
    
    # Filesystem paths
    scan_results_path = Column(String(512), nullable=True)
    
    # Selection metadata
    is_selected_by_llm = Column(Boolean, default=False, nullable=False)
    is_manually_selected = Column(Boolean, default=False, nullable=False)  # User override
    is_manually_deselected = Column(Boolean, default=False, nullable=False)  # User explicitly excluded
    
    # Cache Analytics
    content_hash_current = Column(String(64), nullable=True)
    content_hash_previous = Column(String(64), nullable=True)
    llm_analysis_cached = Column(Boolean, default=False)
    cache_hit_reason = Column(String(50), nullable=True)
    
    # Timestamps (created_at and updated_at inherited from BaseModel)
    scanned_at = Column(DateTime, nullable=True)
    
    @property
    def is_selected(self) -> bool:
        """Compute final selection status with user override priority."""
        # Manual selection always wins
        if self.is_manually_selected:
            return True
        # Manual deselection blocks LLM selection
        if self.is_manually_deselected:
            return False
        # Default to LLM decision
        return self.is_selected_by_llm
    
    # Constraints
    __table_args__ = (
        Index('idx_scan_pages_score', 'score_overall'),
    )
