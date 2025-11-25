from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from datetime import datetime
from urllib.parse import urlparse
import hashlib

from app.features.scan.schemas.scan import (
    ScanStartRequest, 
    ScanStartResponse,
    ScanStatusResponse,
    ScanResultsResponse
)
from app.features.scan.models.scan_job import ScanJob
from app.features.scan.models.scan_page import ScanPage
from app.features.sites.models.site import Site
from app.features.scan.services.discovery.page_discovery import PageDiscoveryService
from app.features.scan.services.analysis.page_selector import PageSelectorService
from app.platform.response import api_response
from app.platform.db.session import get_db

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/start", response_model=ScanStartResponse)
async def start_scan(
    data: ScanStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a complete website scan (SYNCHRONOUS FOR NOW - NO QUEUE YET).
        
    Returns:
        ScanStartResponse with job_id and results summary
    """
    try:
        url_str = str(data.url)
        parsed = urlparse(url_str)
        domain = parsed.netloc
        
        normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        
        # Check if Site exists, create if not
        site_query = select(Site).where(
            Site.root_url == url_str,
            Site.user_id == None 
        )
        result = await db.execute(site_query)
        site = result.scalar_one_or_none()
        
        if not site:
            site = Site(
                user_id=None,
                root_url=url_str,
                root_url_normalized=normalized_url,
                domain=domain,
                total_scans=0
            )
            db.add(site)
            await db.flush() 
        
        # Create ScanJob
        # Generate device_id for anonymous scans. Tests
        device_id = None if data.user_id else f"anonymous-{hashlib.sha256(url_str.encode()).hexdigest()[:16]}"
        
        scan_job = ScanJob(
            user_id=data.user_id,  # Set if authenticated
            device_id=device_id,  # Set for anonymous scans
            site_id=site.id,
            status="discovering",
            queued_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )
        db.add(scan_job)
        await db.flush()
        
        
        discovery_service = PageDiscoveryService()
        discovered_pages = discovery_service.discover_pages(
            url=url_str,
            max_pages=100
        )
        
        scan_job.pages_discovered = len(discovered_pages)
        scan_job.status = "selecting"
        
        
        for page_url in discovered_pages:
            page_normalized = page_url.rstrip('/')
            scan_page = ScanPage(
                scan_job_id=scan_job.id,
                page_url=page_url,
                page_url_normalized=page_normalized,
                is_selected_by_llm=False,  # Will be updated after selection
                is_manually_selected=False,
                is_manually_deselected=False
            )
            db.add(scan_page)
        
        await db.flush() 
        
        
        selector_service = PageSelectorService()
        selected_urls = selector_service.filter_important_pages(
            pages=discovered_pages,
            top_n=data.top_n,
            referer=url_str,
            site_title=domain
        )
        
        scan_job.pages_selected = len(selected_urls)
        scan_job.status = "completed"  # No scraping/analysis yet
        scan_job.completed_at = datetime.utcnow()
        
        
        selected_normalized = {url.rstrip('/') for url in selected_urls}
        pages_query = select(ScanPage).where(ScanPage.scan_job_id == scan_job.id)
        pages_result = await db.execute(pages_query)
        all_pages = pages_result.scalars().all()
        
        for page in all_pages:
            if page.page_url_normalized in selected_normalized:
                page.is_selected_by_llm = True
        
        # Update site stats
        site.total_scans += 1
        site.last_scanned_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(scan_job)
        
        return api_response(
            data={
                "job_id": scan_job.id,
                "status": scan_job.status,
                "message": f"Scan completed! Discovered {scan_job.pages_discovered} pages, selected {scan_job.pages_selected} for analysis."
            }
        )
        
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error starting scan: {str(e)}",
            data={}
        )


@router.get("/{job_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current status of a scan job.
    
    Returns progress information for all phases:
    - discovery: queued/in_progress/completed/failed
    - selection: queued/in_progress/completed/failed
    - scraping: queued/in_progress/completed/failed
    - extraction: queued/in_progress/completed/failed
    - analysis: queued/in_progress/completed/failed
    - aggregation: queued/in_progress/completed/failed
    
    Args:
        job_id: The scan job ID
        db: Database session
        
    Returns:
        ScanStatusResponse with detailed progress
    """
    try:
        # TODO: Query ScanJob by job_id
        # TODO: Return current phase statuses
        
        return api_response(
            data={
                "job_id": job_id,
                "status": "in_progress",
                "current_phase": "discovery",
                "progress": {
                    "discovery": "completed",
                    "selection": "in_progress",
                    "scraping": "queued",
                    "extraction": "queued",
                    "analysis": "queued",
                    "aggregation": "queued"
                }
            }
        )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching scan status: {str(e)}",
            data={}
        )


@router.get("/{job_id}/results", response_model=ScanResultsResponse)
async def get_scan_results(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the final results of a completed scan.
    
    Only returns data if scan status is 'completed'.
    Returns aggregated issues, accessibility score, performance metrics, etc.
    
    Args:
        job_id: The scan job ID
        db: Database session
        
    Returns:
        ScanResultsResponse with all findings
    """
    try:
        # TODO: Query ScanJob and verify completed
        # TODO: Query all ScanIssues for this job
        # TODO: Return aggregated results
        
        return api_response(
            data={
                "job_id": job_id,
                "status": "completed",
                "results": {
                    "issues_found": 0,
                    "accessibility_score": 0,
                    "performance_score": 0
                }
            }
        )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching scan results: {str(e)}",
            data={}
        )
