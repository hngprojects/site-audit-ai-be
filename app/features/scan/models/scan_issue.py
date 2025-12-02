from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Index, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.platform.db.base import BaseModel


class IssueCategory(enum.Enum):
    """Issue category classification"""
    seo = "seo"
    accessibility = "accessibility"
    design = "design"
    performance = "performance"


class IssueSeverity(enum.Enum):
    """Issue severity levels"""
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class ScanIssue(BaseModel):
    """
    Specific issues/recommendations found during page analysis.
    
    Each issue represents a single finding (e.g., "Missing alt text on image").
    """
    __tablename__ = "scan_issues"
    
    # Foreign Keys
    scan_page_id = Column(String, ForeignKey("scan_pages.id", ondelete="CASCADE"), nullable=False, index=True)
    scan_job_id = Column(String, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Issue classification
    category = Column(Enum(IssueCategory), nullable=False, index=True)
    severity = Column(Enum(IssueSeverity), nullable=False, index=True)
    
    # Issue details
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)

    # Element context (if applicable)
    element_selector = Column(String(512), nullable=True)  # CSS selector
    element_html = Column(Text, nullable=True)  # Snippet of problematic HTML
    
    # Impact assessment
    impact_score = Column(Float, nullable=True)  # 0.0-10.0
    
    # Additional requirements
    affected_elements_count = Column(Integer, nullable=True, default=0)  # Number of affected elements
    business_impact = Column(Text, nullable=True)  # Business consequences explanation
    resources = Column(JSON, nullable=True)  # Helpful links/documentation as JSON array
    
    # Relationships
    scan_page = relationship("ScanPage", back_populates="issues", lazy="select")
    scan_job = relationship("ScanJob", lazy="select")
    
    # Constraints
    __table_args__ = (
        Index('idx_scan_issues_category', 'category'),
        Index('idx_scan_issues_severity', 'severity'),
    )
