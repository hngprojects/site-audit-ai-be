from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Optional
import hashlib
import logging

from app.features.scan.schemas.scan import (
    ScanStartRequest, 
    ScanStartResponse,
    ScanStatusResponse,
    ScanResultsResponse,
    ScanHistoryItem
)
from app.features.auth.routes.auth import get_current_user
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.features.sites.models.site import Site
from app.features.scan.services.discovery.page_discovery import PageDiscoveryService
from app.features.scan.services.analysis.page_selector import PageSelectorService
from app.features.scan.services.orchestration.history import get_user_scan_history
from app.platform.response import api_response
from app.platform.db.session import get_db
from app.features.scan.services.orchestration.periodic_scans import get_user_periodic_scans

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/start", response_model=ScanStartResponse)
async def start_scan(
    data: ScanStartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    """
    Start a complete website scan (SYNCHRONOUS - for testing).
    
    This endpoint runs the full scan synchronously:
    1. Discovers pages using Selenium
    2. Selects important pages using LLM
    3. Returns results immediately
    
    Use /start-async for production async workflow.
    
    Supports both authenticated and anonymous users.
        
    Returns:
        ScanStartResponse with job_id and results summary
    """
    try:
        url_str = str(data.url)
        parsed = urlparse(url_str)
        
        # Extract user_id from token if authenticated
        user_id = None
        if credentials:
            try:
                from app.features.auth.routes.auth import decode_access_token
                payload = decode_access_token(credentials.credentials)
                user_id = payload.get("sub")
            except Exception as e:
                pass  # If token is invalid, treat as anonymous
        
        # Fallback to request body user_id if not authenticated
        if not user_id:
            user_id = data.user_id
        
        # Generate device_id for anonymous users (needed for both Site and ScanJob)
        device_id = None if user_id else f"anonymous-{hashlib.sha256(url_str.encode()).hexdigest()[:16]}"
        
        # Check if Site exists for this user (or anonymous), create if not
        if user_id:
            # For authenticated users, check for their site
            site_query = select(Site).where(
                Site.root_url == url_str,
                Site.user_id == user_id
            )
        else:
            # For anonymous users, check for anonymous site by device_id
            site_query = select(Site).where(
                Site.root_url == url_str,
                Site.device_id == device_id
            )
        result = await db.execute(site_query)
        site = result.scalar_one_or_none()
        
        if not site:
            site = Site(
                user_id=user_id,
                device_id=device_id,  # Include device_id for anonymous users
                root_url=url_str,
                total_scans=0
            )
            db.add(site)
            await db.flush() 
        
        # Create ScanJob
        
        scan_job = ScanJob(
            user_id=user_id,  # Set if authenticated
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
        scan_job.status = ScanJobStatus.selecting
        
        
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
        )
        
        scan_job.pages_selected = len(selected_urls)
        scan_job.status = ScanJobStatus.completed 
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
        logger.error(f"Error starting sync scan: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error starting scan: {str(e)}",
            data={}
        )


@router.post("/start-async", response_model=ScanStartResponse)
async def start_scan_async(
    data: ScanStartRequest,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    """
    Start a complete website scan (ASYNC - for production).
    
    This endpoint queues the scan to Celery workers and returns immediately.
    Use GET /scan/{job_id}/status to poll for progress.
    
    The scan pipeline runs as:
    1. Discovery (Selenium crawler)
    2. Selection (LLM picks important pages)
    3. Scraping (fetch HTML for each page)
    4. Extraction (parse structured data)
    5. Analysis (LLM scores each page)
    6. Aggregation (combine into final scores)
    
    Supports both authenticated and anonymous users.
    
    Returns:
        ScanStartResponse with job_id for tracking
    """
    from app.features.scan.workers.tasks import run_scan_pipeline
    
    try:
        url_str = str(data.url)
        parsed = urlparse(url_str)
        
        # Extract user_id from token if authenticated
        user_id = None
        if credentials:
            try:
                from app.features.auth.routes.auth import decode_access_token
                payload = decode_access_token(credentials.credentials)
                user_id = payload.get("sub")
            except Exception as e:
                pass  # If token is invalid, treat as anonymous
        
        # Fallback to request body user_id if not authenticated
        if not user_id:
            user_id = data.user_id
        
        # Generate device_id for anonymous users (needed for both Site and ScanJob)
        device_id = None if user_id else f"anonymous-{hashlib.sha256(url_str.encode()).hexdigest()[:16]}"
        
        # Check if Site exists for this user (or anonymous), create if not
        if user_id:
            # For authenticated users, check for their site
            site_query = select(Site).where(
                Site.root_url == url_str,
                Site.user_id == user_id
            )
        else:
            # For anonymous users, check for anonymous site by device_id
            site_query = select(Site).where(
                Site.root_url == url_str,
                Site.device_id == device_id
            )
        result = await db.execute(site_query)
        site = result.scalar_one_or_none()
        
        if not site:
            site = Site(
                user_id=user_id,
                device_id=device_id,
                root_url=url_str,
                total_scans=0
            )
            db.add(site)
            await db.flush() 
        
        # Create ScanJob with queued status
        
        scan_job = ScanJob(
            user_id=user_id,
            device_id=device_id,
            site_id=site.id,
            status="queued",
            queued_at=datetime.utcnow()
        )
        db.add(scan_job)
        await db.commit()
        await db.refresh(scan_job)
        
        # Queue the scan pipeline to Celery
        run_scan_pipeline.delay(
            job_id=scan_job.id,
            url=url_str,
            top_n=data.top_n,
            max_pages=100
        )
        
        logger.info(f"Queued async scan job {scan_job.id} for {url_str}")
        
        return api_response(
            data={
                "job_id": scan_job.id,
                "status": "queued",
                "message": f"Scan queued successfully. Poll GET /scan/{scan_job.id}/status for progress."
            }
        )
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error starting async scan: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error starting scan: {str(e)}",
            data={}
        )


@router.get("/history", response_model=List[ScanHistoryItem])
async def get_scan_history(
    limit: int = 10,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """ 
    Get scan history for the authenticated user.
    
    Args:
        limit: Number of recent scans to return
        current_user: The authenticated user
        db: Database session
        
    Returns:
        List of ScanHistoryItem with summary of past scans
    """
    
    logger.info(f"User {current_user.id} fetching scan history (Limit: {limit})")
    
    scans = await get_user_scan_history(user_id=current_user.id, db=db, limit=limit)
    return scans


@router.get("/periodic-scans", response_model=dict)
async def get_user_periodic_scans_route(
    limit: int = 20,
    status: Optional[str] = None,
    site_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all periodic scans for the authenticated user across all their sites.
    
    This endpoint returns scans that were automatically triggered by the 
    periodic scanning system (via Celery Beat).
    
    Query Parameters:
        - limit: Number of scans to return (default: 20, max: 100)
        - status: Filter by scan status (queued, discovering, completed, etc.)
        - site_id: Filter by specific site ID
        
    Returns:
        List of periodic scan jobs with site information and results
    """
    # Validate and cap limit
    if limit > 100:
        limit = 100
    
    logger.info(f"User {current_user.id} fetching periodic scans (Limit: {limit})")
    
    scans = await get_user_periodic_scans(
        user_id=current_user.id,
        db=db,
        limit=limit,
        status_filter=status,
        site_id_filter=site_id
    )
    
    return api_response(
        data={
            "total_scans": len(scans),
            "scans": scans
        },
        message="Periodic scans retrieved successfully",
        status_code=status.HTTP_200_OK
    )


@router.get("/{job_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current status of a scan job.
    
    Returns progress information for all phases:
    - queued: Job is waiting to start
    - discovering: Finding pages on the site
    - selecting: LLM choosing important pages
    - processing: Scraping/extracting/analyzing pages
    - completed: All done
    - failed: Something went wrong
    
    Args:
        job_id: The scan job ID
        db: Database session
        
    Returns:
        ScanStatusResponse with detailed progress
    """
    try:
        # Query ScanJob by job_id
        job_query = select(ScanJob).where(ScanJob.id == job_id)
        result = await db.execute(job_query)
        job = result.scalar_one_or_none()
        
        if not job:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Scan job {job_id} not found",
                data={}
            )
        
        # Simple intelligent progress calculation
        status_str = job.status.value if hasattr(job.status, 'value') else str(job.status)
        
        # Calculate overall progress percentage
        if status_str == "queued":
            progress_percent = 0
            current_step = "Waiting to start"
        elif status_str == "discovering":
            progress_percent = 10
            current_step = f"Finding pages on site"
        elif status_str == "selecting":
            progress_percent = 30
            current_step = f"Selecting important pages from {job.pages_discovered or 0} discovered pages"
        elif status_str == "scraping":
            progress_percent = 40
            current_step = f"Scraping {job.pages_selected or 0} pages"
        elif status_str == "analyzing":
            progress_percent = 60
            current_step = "Analyzing content"
        elif status_str == "aggregating":
            progress_percent = 90
            current_step = "Calculating final scores"
        elif status_str == "completed":
            progress_percent = 100
            current_step = "Scan complete"
        elif status_str == "failed":
            progress_percent = 0
            current_step = "Scan failed"
        else:
            progress_percent = 0
            current_step = "Unknown status"
        
        return api_response(
            data={
                "job_id": job_id,
                "status": status_str,
                "progress_percent": progress_percent,
                "current_step": current_step,
                "pages_discovered": job.pages_discovered,
                "pages_selected": job.pages_selected,
                "pages_scanned": job.pages_scanned,
                "error_message": job.error_message,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching scan status: {e}")
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
    Returns aggregated issues, scores, and page-level results.
    
    Args:
        job_id: The scan job ID
        db: Database session
        
    Returns:
        ScanResultsResponse with all findings
    """
    try:
        # Query ScanJob and verify completed
        job_query = select(ScanJob).where(ScanJob.id == job_id)
        result = await db.execute(job_query)
        job = result.scalar_one_or_none()
        
        if not job:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Scan job {job_id} not found",
                data={}
            )
        
        if job.status != ScanJobStatus.completed:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Scan is not completed yet. Current status: {job.status.value}",
                data={"status": job.status.value}
            )
        
        # Query all pages for this job
        pages_query = select(ScanPage).where(ScanPage.scan_job_id == job_id)
        pages_result = await db.execute(pages_query)
        all_pages = pages_result.scalars().all()
        
        # Build results with detailed analysis
        selected_pages = [
            {
                "url": page.page_url,
                "score_overall": page.score_overall,
                "score_seo": page.score_seo,
                "score_accessibility": page.score_accessibility,
                "score_performance": page.score_performance,
                "score_design": page.score_design,
                "critical_issues": page.critical_issues_count,
                "warnings": page.warning_issues_count,
                "analysis_details": page.analysis_details  # Full LLM analysis
            }
            for page in all_pages if page.is_selected_by_llm
        ]
        
        return api_response(
            data={
                "job_id": job_id,
                "status": job.status,
                "results": {
                    "score_overall": job.score_overall or 0,
                    "score_seo": job.score_seo or 0,
                    "score_accessibility": job.score_accessibility or 0,
                    "score_performance": job.score_performance or 0,
                    "score_design": job.score_design or 0,
                    "total_issues": job.total_issues,
                    "critical_issues": job.critical_issues_count,
                    "warnings": job.warning_issues_count,
                    "pages_discovered": job.pages_discovered,
                    "pages_selected": job.pages_selected,
                    "pages_analyzed": job.pages_llm_analyzed,
                    "selected_pages": selected_pages
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching scan results: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching scan results: {str(e)}",
            data={}
        )


@router.get("/{job_id}/pages")
async def get_scan_pages(
    job_id: str,
    selected_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pages discovered/selected for a scan job.
    
    Args:
        job_id: The scan job ID
        selected_only: If True, only return LLM-selected pages
        db: Database session
        
    Returns:
        List of pages with their selection status
    """
    try:
        # Verify job exists
        job_query = select(ScanJob).where(ScanJob.id == job_id)
        result = await db.execute(job_query)
        job = result.scalar_one_or_none()
        
        if not job:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Scan job {job_id} not found",
                data={}
            )
        
        # Query pages
        pages_query = select(ScanPage).where(ScanPage.scan_job_id == job_id)
        if selected_only:
            pages_query = pages_query.where(ScanPage.is_selected_by_llm == True)
        
        pages_result = await db.execute(pages_query)
        all_pages = pages_result.scalars().all()
        
        pages_data = [
            {
                "id": page.id,
                "url": page.page_url,
                "is_selected_by_llm": page.is_selected_by_llm,
                "is_manually_selected": page.is_manually_selected,
                "is_manually_deselected": page.is_manually_deselected,
                "score_overall": page.score_overall
            }
            for page in all_pages
        ]
        
        return api_response(
            data={
                "job_id": job_id,
                "pages": pages_data,
                "count": len(pages_data),
                "total_discovered": job.pages_discovered,
                "total_selected": job.pages_selected
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching scan pages: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching scan pages: {str(e)}",
            data={}
        )