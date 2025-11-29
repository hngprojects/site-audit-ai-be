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
        issue: ScanIssue database object (already loaded)
        
    Returns:
        Dictionary matching IssueSummary schema
    """
    # Get page URL from relationship (already eager loaded)
    page_url = "Unknown"
    if issue.scan_page:
        # Access page_url without triggering async loader
        page_url = issue.scan_page.__dict__.get('page_url', 'Unknown')
    
    # Use description as short_description (truncate if too long)
    short_desc = issue.__dict__.get('description', '')
    if len(short_desc) > 200:
        short_desc = short_desc[:197] + "..."
    
    # Access enums via __dict__ to avoid async issues
    category_obj = issue.__dict__.get('category')
    severity_obj = issue.__dict__.get('severity')
    
    return {
        "id": issue.__dict__.get('id'),
        "title": issue.__dict__.get('title'),
        "category": category_obj.value if isinstance(category_obj, IssueCategory) else str(category_obj),
        "severity": severity_obj.value if isinstance(severity_obj, IssueSeverity) else str(severity_obj),
        "score_impact": issue.__dict__.get('impact_score'),
        "page_url": page_url,
        "short_description": short_desc,
        "affected_elements_count": issue.__dict__.get('affected_elements_count') or 0
    }


def format_issue_detail(issue: ScanIssue) -> Dict[str, Any]:
    """
    Format a ScanIssue object as an IssueDetail dict for API response.
    
    Args:
        issue: ScanIssue database object with relationships loaded
        
    Returns:
        Dictionary matching IssueDetail schema
    """
    # Get page and job info from relationships (already eager loaded)
    page_url = "Unknown"
    if issue.scan_page:
        # Access page_url without triggering async loader
        page_url = issue.scan_page.__dict__.get('page_url', 'Unknown')
    page_id = issue.__dict__.get('scan_page_id')
    job_id = issue.__dict__.get('scan_job_id')
    
    # Format affected elements
    affected_elements = []
    element_selector = issue.__dict__.get('element_selector')
    element_html = issue.__dict__.get('element_html')
    if element_selector or element_html:
        affected_elements.append({
            "selector": element_selector,
            "html": element_html
        })
    
    # Parse resources from JSON
    resources = []
    resources_data = issue.__dict__.get('resources')
    if resources_data:
        if isinstance(resources_data, list):
            resources = resources_data
        elif isinstance(resources_data, dict):
            resources = [resources_data]
    
    # Access enums via __dict__
    category_obj = issue.__dict__.get('category')
    severity_obj = issue.__dict__.get('severity')
    created_at = issue.__dict__.get('created_at')
    
    return {
        "id": issue.__dict__.get('id'),
        "title": issue.__dict__.get('title'),
        "category": category_obj.value if isinstance(category_obj, IssueCategory) else str(category_obj),
        "severity": severity_obj.value if isinstance(severity_obj, IssueSeverity) else str(severity_obj),
        "description": issue.__dict__.get('description'),
        "what_this_means": issue.__dict__.get('what_this_means'),
        "recommendation": issue.__dict__.get('recommendation'),
        "score_impact": issue.__dict__.get('impact_score'),
        "page_url": page_url,
        "page_id": page_id,
        "job_id": job_id,
        "business_impact": issue.__dict__.get('business_impact'),
        "affected_elements_count": issue.__dict__.get('affected_elements_count') or 0,
        "affected_elements": affected_elements,
        "resources": resources,
        "created_at": created_at.isoformat() if created_at else None
    }


def count_issues_by_severity(issues: List[ScanIssue]) -> Dict[str, int]:
    """
    Count issues by severity level.
    
    Args:
        issues: List of ScanIssue objects (already loaded)
        
    Returns:
        Dictionary with counts: {critical: int, warning: int, info: int}
    """
    counts = {
        "critical": 0,
        "warning": 0,  # high + medium
        "info": 0      # low + info
    }
    
    for issue in issues:
        # Access via __dict__ to avoid triggering async loader
        severity_obj = issue.__dict__.get('severity')
        if severity_obj is None:
            continue
            
        severity = severity_obj.value if isinstance(severity_obj, IssueSeverity) else str(severity_obj)
        
        if severity == "critical":
            counts["critical"] += 1
        elif severity in ["high", "medium"]:
            counts["warning"] += 1
        elif severity in ["low", "info"]:
            counts["info"] += 1
    
    return counts
