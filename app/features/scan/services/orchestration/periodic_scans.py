from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.features.scan.models.scan_job import ScanJob
from app.features.sites.models.site import Site


async def get_user_periodic_scans(
    user_id: str,
    db: AsyncSession,
    limit: int = 20,
    status_filter: Optional[str] = None,
    site_id_filter: Optional[str] = None
) -> List[dict]:
    """
    Get all periodic scans for a user across all their sites.
    
    Args:
        user_id: The authenticated user's ID
        db: Database session
        limit: Maximum number of scans to return
        status_filter: Optional filter by scan status
        site_id_filter: Optional filter by specific site
        
    Returns:
        List of periodic scan items with site information
    """
    # Build query joining scan_jobs with sites
    query = (
        select(ScanJob, Site)
        .join(Site, ScanJob.site_id == Site.id)
        .where(
            Site.user_id == user_id,
            Site.scan_frequency_enabled == True
        )
    )
    
    # Apply optional filters
    if status_filter:
        query = query.where(ScanJob.status == status_filter)
    
    if site_id_filter:
        query = query.where(Site.id == site_id_filter)
    
    # Order by most recent first and limit
    query = query.order_by(ScanJob.created_at.desc()).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    rows = result.all()
    
    # Transform to response format
    scans = []
    for scan_job, site in rows:
        scans.append({
            "job_id": scan_job.id,
            "site_id": site.id,
            "site_url": site.root_url,
            "site_display_name": site.display_name,
            "scan_frequency": site.scan_frequency.value,
            "status": scan_job.status.value if hasattr(scan_job.status, 'value') else str(scan_job.status),
            "score_overall": scan_job.score_overall,
            "score_seo": scan_job.score_seo,
            "score_accessibility": scan_job.score_accessibility,
            "score_performance": scan_job.score_performance,
            "score_design": scan_job.score_design,
            "total_issues": scan_job.total_issues or 0,
            "critical_issues_count": scan_job.critical_issues_count or 0,
            "warning_issues_count": scan_job.warning_issues_count or 0,
            "created_at": scan_job.created_at,
            "completed_at": scan_job.completed_at
        })
    
    return scans