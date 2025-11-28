"""
Issue Service

Business logic for fetching and formatting scan issues.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.features.scan.models.scan_issue import ScanIssue, IssueCategory, IssueSeverity
from app.features.scan.models.scan_page import ScanPage
from app.features.scan.models.scan_job import ScanJob


async def get_issues_for_job(db: AsyncSession, job_id: str) -> List[ScanIssue]:
    """
    Fetch all issues for a given scan job.
    
    Args:
        db: Database session
        job_id: Scan job ID
        
    Returns:
        List of ScanIssue objects with page relationship loaded
    """
    query = (
        select(ScanIssue)
        .where(ScanIssue.scan_job_id == job_id)
        .options(joinedload(ScanIssue.scan_page))  # Eager load page relationship
        .order_by(
            # Order by severity (critical first), then by category
            ScanIssue.severity,
            ScanIssue.category
        )
    )
    
    result = await db.execute(query)
    issues = result.scalars().unique().all()
    return list(issues)


async def get_issue_by_id(db: AsyncSession, issue_id: str) -> Optional[ScanIssue]:
    """
    Fetch a single issue by ID with all related data.
    
    Args:
        db: Database session
        issue_id: Issue ID
        
    Returns:
        ScanIssue object with relationships loaded, or None if not found
    """
    query = (
        select(ScanIssue)
        .where(ScanIssue.id == issue_id)
        .options(
            joinedload(ScanIssue.scan_page),  # Load page
            joinedload(ScanIssue.scan_job)    # Load job
        )
    )
    
    result = await db.execute(query)
    issue = result.scalar_one_or_none()
    return issue


def format_issue_summary(issue: ScanIssue) -> Dict[str, Any]:
    """
    Format a ScanIssue object as an IssueSummary dict for API response.
    
    Args:
        issue: ScanIssue database object
        
    Returns:
        Dictionary matching IssueSummary schema
    """
    # Get page URL from relationship
    page_url = issue.scan_page.page_url if issue.scan_page else "Unknown"
    
    # Use description as short_description (truncate if too long)
    short_desc = issue.description
    if len(short_desc) > 200:
        short_desc = short_desc[:197] + "..."
    
    return {
        "id": issue.id,
        "title": issue.title,
        "category": issue.category.value if isinstance(issue.category, IssueCategory) else issue.category,
        "severity": issue.severity.value if isinstance(issue.severity, IssueSeverity) else issue.severity,
        "score_impact": issue.impact_score,
        "page_url": page_url,
        "short_description": short_desc,
        "affected_elements_count": issue.affected_elements_count or 0
    }


def format_issue_detail(issue: ScanIssue) -> Dict[str, Any]:
    """
    Format a ScanIssue object as an IssueDetail dict for API response.
    
    Args:
        issue: ScanIssue database object with relationships loaded
        
    Returns:
        Dictionary matching IssueDetail schema
    """
    # Get page and job info from relationships
    page_url = issue.scan_page.page_url if issue.scan_page else "Unknown"
    page_id = issue.scan_page_id
    job_id = issue.scan_job_id
    
    # Format affected elements
    affected_elements = []
    if issue.element_selector or issue.element_html:
        affected_elements.append({
            "selector": issue.element_selector,
            "html": issue.element_html
        })
    
    # Parse resources from JSON
    resources = []
    if issue.resources:
        if isinstance(issue.resources, list):
            resources = issue.resources
        elif isinstance(issue.resources, dict):
            resources = [issue.resources]
    
    return {
        "id": issue.id,
        "title": issue.title,
        "category": issue.category.value if isinstance(issue.category, IssueCategory) else issue.category,
        "severity": issue.severity.value if isinstance(issue.severity, IssueSeverity) else issue.severity,
        "description": issue.description,
        "what_this_means": issue.what_this_means,
        "recommendation": issue.recommendation,
        "score_impact": issue.impact_score,
        "page_url": page_url,
        "page_id": page_id,
        "job_id": job_id,
        "business_impact": issue.business_impact,
        "affected_elements_count": issue.affected_elements_count or 0,
        "affected_elements": affected_elements,
        "resources": resources,
        "created_at": issue.created_at.isoformat() if issue.created_at else None
    }


def count_issues_by_severity(issues: List[ScanIssue]) -> Dict[str, int]:
    """
    Count issues by severity level.
    
    Args:
        issues: List of ScanIssue objects
        
    Returns:
        Dictionary with counts: {critical: int, warning: int, info: int}
    """
    counts = {
        "critical": 0,
        "warning": 0,  # high + medium
        "info": 0      # low + info
    }
    
    for issue in issues:
        severity = issue.severity.value if isinstance(issue.severity, IssueSeverity) else issue.severity
        
        if severity == "critical":
            counts["critical"] += 1
        elif severity in ["high", "medium"]:
            counts["warning"] += 1
        elif severity in ["low", "info"]:
            counts["info"] += 1
    
    return counts
