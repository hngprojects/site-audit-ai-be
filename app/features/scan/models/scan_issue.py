from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Index
from datetime import datetime

from app.platform.db.base import BaseModel


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
    category = Column(String(50), nullable=False, index=True)  # 'seo', 'accessibility', 'design', 'performance' Maybe we use an ENUM herre?
    severity = Column(String(50), nullable=False, index=True)  # 'critical', 'high', 'medium', 'low', 'info' Enum here too? @apathy @phurhard @Muizzyranking @Newkoncept @others; lets discuss
    
    # Issue details
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=False)
    what_this_means = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    #What field to use for 'What this means'?

    # Element context (if applicable)
    element_selector = Column(String(512), nullable=True)  # CSS selector
    element_html = Column(Text, nullable=True)  # Snippet of problematic HTML
    
    # Impact assessment
    impact_score = Column(Float, nullable=True)  # 0.0-10.0
    
    # Constraints
    __table_args__ = (
        Index('idx_scan_issues_category', 'category'),
        Index('idx_scan_issues_severity', 'severity'),
    )
