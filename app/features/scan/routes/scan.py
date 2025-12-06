import asyncio
import redis
import json
import hashlib
from urllib.parse import urlparse
from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Response
from sqlalchemy import select, func
from sqlalchemy.orm import aliased
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Optional
import hashlib
from app.platform.logger import get_logger
from app.platform.utils.device import parse_device_header, generate_ip_fingerprint
from app.features.scan.services.device.device_service import (
    get_or_create_device_session,
    check_rate_limit,
    increment_scan_count
)
from app.features.scan.schemas.scan import (
    ScanStartRequest,
    ScanStartResponse,
    ScanStatusResponse,
    ScanResultsResponse,
    ScanHistoryItem, 
)
from app.features.scan.workers.tasks import run_single_page_scan_sse
from app.features.auth.routes.auth import get_current_user, decode_access_token
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.features.scan.models.scan_issue import ScanIssue
from app.features.sites.models.site import Site
from app.features.scan.services.discovery.page_discovery import PageDiscoveryService
from app.features.scan.services.analysis.page_selector import PageSelectorService
from app.features.scan.services.analysis.page_analyzer import PageAnalyzerService
from app.features.scan.services.orchestration.history import get_user_scan_history
from app.features.scan.services.scan.scan import stop_scan_job
from app.platform.response import api_response
from app.platform.config import settings
from app.platform.db.session import get_db
from app.features.scan.services.utils.scan_result_parser import parse_audit_report, generate_summary_message
from app.features.scan.services.utils.issues_list_parser import parse_detailed_audit_report
from app.platform.utils.url_validator import validate_url

from app.features.scan.services.orchestration.periodic_scans import get_user_periodic_scans

logger = get_logger(__name__)

router = APIRouter(prefix="/scan", tags=["scan"])

@router.post("/start-scan-sse")
async def start_scan_sse(
    url: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    try:

        is_valid, url_str, error_message = validate_url(url)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid URL: {error_message}"
            )
        
        parsed = urlparse(url_str)
        
        # Extract user_id from token if authenticated
        user_id = None
        if credentials:
            try:
                payload = decode_access_token(credentials.credentials)
                user_id = payload.get("sub")
            except Exception:
                pass
        
        device_id_raw, platform = parse_device_header(request)
        
        # Generate device_id if not provided (for web users)
        if not device_id_raw:
            device_id_raw = generate_ip_fingerprint(request)
            platform = "web"
            if not user_id:
                logger.warning(f"[SSE] No device_id provided for {url_str}, using IP fallback")
        
        # Log authentication status for error tracking
        is_ip_fallback = device_id_raw.startswith("ip-")
        auth_status = "authenticated" if user_id else "device_id" if not is_ip_fallback else "ip_fallback"
        logger.info(f"[SSE] Scan request: url={url_str}, auth_status={auth_status}, user_id={user_id}, platform={platform}")
        
        # Get or create device session for tracking (always has device_id_raw now)
        user_agent = request.headers.get("user-agent")
        device_session = await get_or_create_device_session(
            db=db,
            device_id=device_id_raw,
            platform=platform,
            user_agent=user_agent,
            user_id=user_id
        )
        
        # Check rate limits
        is_allowed, remaining, message = await check_rate_limit(db, device_session, user_id, is_ip_fallback)
        if not is_allowed:
            logger.warning(f"[SSE] Rate limit exceeded: {message} (user_id={user_id}, device={device_session.device_hash[:8]}...)")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. {message}. Please try again tomorrow."
            )
        
        # For ScanJob: use device_id only for anonymous users
        device_id_for_scan = device_id_raw if not user_id else None
        
        if user_id:
            site_query = select(Site).where(
                Site.root_url == url_str,
                Site.user_id == user_id
            )
        else:
            site_query = select(Site).where(
                Site.root_url == url_str,
                Site.device_id == device_id_for_scan
            )
        
        result = await db.execute(site_query)
        site = result.scalar_one_or_none()
        
        if not site:
            site = Site(
                user_id=user_id,
                device_id=device_id_for_scan,
                root_url=url_str,
                total_scans=0
            )
            db.add(site)
            await db.flush()
        
        scan_job = ScanJob(
            user_id=user_id,
            device_id=device_id_for_scan,
            site_id=site.id,
            status=ScanJobStatus.queued,
            queued_at=datetime.utcnow()
        )
        db.add(scan_job)
        await db.flush()
        
        # Increment scan counter in device session
        await increment_scan_count(db, device_session)
        
        await db.commit()
        await db.refresh(scan_job)
        
        job_id = scan_job.id
        
        logger.info(f"[SSE] Created scan job {job_id} for {url_str} (auth_status={auth_status}, remaining_quota={remaining})")

        run_single_page_scan_sse.delay(job_id, url_str)

        async def event_generator():
            """Generate SSE events from Redis pub/sub channel"""
            r = redis.from_url(settings.CELERY_RESULT_BACKEND)
            pubsub = r.pubsub()
            channel = f"scan_progress:{job_id}"
            
            try:
                pubsub.subscribe(channel)
                
                yield {
                    "event": "scan_started",
                    "data": json.dumps({
                        "job_id": job_id,
                        "url": url_str,
                        "progress": 0,
                        "message": "Scan started. Analyzing page...",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
                
                for message in pubsub.listen():
                    if await request.is_disconnected():
                        logger.info(f"[SSE] Client disconnected from job {job_id}")
                        break
                    
                    if message['type'] == 'message':
                        try:
                            event_data = json.loads(message['data'])
                            event_type = event_data.get("event_type", "update")
                            
                            yield {
                                "event": event_type,
                                "data": json.dumps(event_data)
                            }
                            
                            logger.info(f"[SSE] Sent {event_type} event to job {job_id}")
                            
                            if event_type in ["scan_complete", "scan_error"]:
                                logger.info(f"[SSE] Closing connection for job {job_id} ({event_type})")
                                break
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"[SSE] Failed to parse event for job {job_id}: {e}")
                            continue

                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"[SSE] Error in event stream for job {job_id}: {e}", exc_info=True)
                yield {
                    "event": "scan_error",
                    "data": json.dumps({
                        "job_id": job_id,
                        "progress": 0,
                        "message": f"Stream error: {str(e)}",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                }
            finally:
                pubsub.unsubscribe(channel)
                pubsub.close()
                logger.info(f"[SSE] Cleaned up connection for job {job_id}")
        
        return EventSourceResponse(event_generator())
        
    except Exception as e:
        logger.error(f"[SSE] Failed to start scan: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scan: {str(e)}"
        )

@router.post("/start", response_model=ScanStartResponse)
async def start_scan(
    data: ScanStartRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False))
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

        # Parse X-Device header from mobile clients
        device_id_raw, platform = parse_device_header(request)
        
        # Generate device_id if not provided (for web users)
        if not device_id_raw:
            device_id_raw = generate_ip_fingerprint(request)
            platform = "web"
            if not user_id:
                logger.warning(f"[SYNC] No device_id provided for {url_str}, using IP fallback")
        
        # Log authentication status
        is_ip_fallback = device_id_raw.startswith("ip-")
        auth_status = "authenticated" if user_id else "device_id" if not is_ip_fallback else "ip_fallback"
        logger.info(f"[SYNC] Scan request: url={url_str}, auth_status={auth_status}, platform={platform}")
        
        # Get or create device session (always has device_id_raw now)
        user_agent = request.headers.get("user-agent")
        device_session = await get_or_create_device_session(
            db=db,
            device_id=device_id_raw,
            platform=platform,
            user_agent=user_agent,
            user_id=user_id
        )
        
        # Check rate limits
        is_allowed, remaining, message = await check_rate_limit(db, device_session, user_id, is_ip_fallback)
        if not is_allowed:
            logger.warning(f"[SYNC] Rate limit exceeded: {message}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. {message}. Please try again tomorrow."
            )
        
        # For ScanJob: use device_id only for anonymous users
        device_id_for_scan = device_id_raw if not user_id else None

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
                Site.device_id == device_id_for_scan
            )
        result = await db.execute(site_query)
        site = result.scalar_one_or_none()

        if not site:
            site = Site(
                user_id=user_id,
                device_id=device_id_for_scan,  # Include device_id for anonymous users
                root_url=url_str,
                total_scans=0
            )
            db.add(site)
            await db.flush()

        # Create ScanJob

        scan_job = ScanJob(
            user_id=user_id,  # Set if authenticated
            device_id=device_id_for_scan,  # Set for anonymous scans
            site_id=site.id,
            status="discovering",
            queued_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )
        db.add(scan_job)
        await db.flush()
        
        # Increment scan counter
        await increment_scan_count(db, device_session)

        discovery_service = PageDiscoveryService()
        discovered_pages = discovery_service.discover_pages(
            url=url_str,
            max_pages=1
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
        pages_query = select(ScanPage).where(
            ScanPage.scan_job_id == scan_job.id)
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False))
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

        user_id = None
        if credentials:
            try:
                from app.features.auth.routes.auth import decode_access_token
                payload = decode_access_token(credentials.credentials)
                user_id = payload.get("sub")
            except Exception as e:
                pass

        if not user_id:
            user_id = data.user_id

        # Parse X-Device header from mobile clients
        device_id_raw, platform = parse_device_header(request)
        
        # Generate device_id if not provided (for web users)
        if not device_id_raw:
            device_id_raw = generate_ip_fingerprint(request)
            platform = "web"
            if not user_id:
                logger.warning(f"[ASYNC] No device_id provided for {url_str}, using IP fallback")
        
        # Log authentication status
        is_ip_fallback = device_id_raw.startswith("ip-")
        auth_status = "authenticated" if user_id else "device_id" if not is_ip_fallback else "ip_fallback"
        logger.info(f"[ASYNC] Scan request: url={url_str}, auth_status={auth_status}, platform={platform}")
        
        # Get or create device session (always has device_id_raw now)
        user_agent = request.headers.get("user-agent")
        device_session = await get_or_create_device_session(
            db=db,
            device_id=device_id_raw,
            platform=platform,
            user_agent=user_agent,
            user_id=user_id
        )
        
        # Check rate limits
        is_allowed, remaining, message = await check_rate_limit(db, device_session, user_id, is_ip_fallback)
        if not is_allowed:
            logger.warning(f"[ASYNC] Rate limit exceeded: {message}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. {message}. Please try again tomorrow."
            )
        
        # For ScanJob: use device_id only for anonymous users
        device_id_for_scan = device_id_raw if not user_id else None

        if user_id:
            site_query = select(Site).where(
                Site.root_url == url_str,
                Site.user_id == user_id
            )
        else:
            site_query = select(Site).where(
                Site.root_url == url_str,
                Site.device_id == device_id_for_scan
            )
        result = await db.execute(site_query)
        site = result.scalar_one_or_none()

        if not site:
            site = Site(
                user_id=user_id,
                device_id=device_id_for_scan,
                root_url=url_str,
                total_scans=0
            )
            db.add(site)
            await db.flush()

        scan_job = ScanJob(
            user_id=user_id,
            device_id=device_id_for_scan,
            site_id=site.id,
            status="queued",
            queued_at=datetime.utcnow()
        )
        db.add(scan_job)
        await db.flush()
        
        # Increment scan counter
        await increment_scan_count(db, device_session)
        
        await db.commit()
        await db.refresh(scan_job)

        task_result = run_scan_pipeline.delay(
            job_id=scan_job.id,
            url=url_str,
            top_n=data.top_n,
            max_pages=1
        )
        scan_job.celery_task_id = task_result.id
        await db.commit()

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
        List of past scans
    """

    logger.info(
        f"User {current_user.id} fetching scan history (Limit: {limit})")

    scans = await get_user_scan_history(user_id=current_user.id, db=db, limit=limit)
    return scans

@router.get("/scans", status_code=200)
async def list_user_scans(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all websites the user has scanned, with the site URL and the date of their latest scan.
    Historical device scans are backfilled with user_id on login.
    
    Returns:
        List of ScanHistoryItem with summary of past scans
    """
    try:
        # Simple query: just filter by user_id
        # Historical device scans are backfilled on login
        latest_scan_subq = (
            select(
                ScanJob.site_id,
                func.max(ScanJob.updated_at).label("last_scan_date")
            )
            .where(
                ScanJob.user_id == current_user.id,
                ScanJob.updated_at.isnot(None),
                ScanJob.status == 'completed'
            )
            .group_by(ScanJob.site_id)
        ).subquery()

        latest_scan = aliased(ScanJob)

        stmt = (
            select(
                latest_scan_subq.c.site_id,
                ScanPage.page_url.label("site_url"),
                latest_scan_subq.c.last_scan_date,
                latest_scan.score_overall,
                latest_scan.score_seo,
                latest_scan.score_accessibility,
                latest_scan.score_performance
            )
            .join(
                latest_scan,
                (latest_scan.site_id == latest_scan_subq.c.site_id) &
                (latest_scan.updated_at == latest_scan_subq.c.last_scan_date)
            )
            .join(
                ScanPage,
                ScanPage.scan_job_id == latest_scan.id
            )
            .group_by(
                latest_scan_subq.c.site_id,
                ScanPage.page_url,
                latest_scan_subq.c.last_scan_date,
                latest_scan.score_overall,
                latest_scan.score_seo,
                latest_scan.score_accessibility,
                latest_scan.score_performance
            )
            .order_by(latest_scan_subq.c.last_scan_date.desc())
        )

        result = await db.execute(stmt)
        sites = result.all()

        data = [
            {
                "site_id": site.site_id,
                "site_url": site.site_url,
                "last_scan_date": site.last_scan_date.isoformat() if site.last_scan_date else None,
                "score_overall": site.score_overall,
                "score_seo": site.score_seo,
                "score_accessibility": site.score_accessibility,
                "score_performance": site.score_performance
            }
            for site in sites
        ]

        return api_response(data=data)

    except Exception as e:
        logger.info(f'Error fetching user websites: {str(e)}')
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Error fetching user websites",
            data={}
        )


@router.get("/periodic-scans", response_model=dict)
async def get_user_periodic_scans_route(
    limit: int = 20,
    status_filter: Optional[str] = None,
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
        status_filter=status_filter,
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
        status_str = job.status.value if hasattr(
            job.status, 'value') else str(job.status)

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
        all_issues = []

        for page in all_pages:
            if page.is_selected_by_llm:
                all_issues.extend(
                    PageAnalyzerService.flatten_issues(page.analysis_details))

        unparsed_result = {
            "job_id": job_id,
            "status": job.status,
            "scanned_at": job.completed_at,
            "results": {
                "score_overall": job.score_overall or 0,
                "score_seo": job.score_seo or 0,
                "score_accessibility": job.score_accessibility or 0,
                "score_performance": job.score_performance or 0,
                "total_issues": job.total_issues,
                "critical_issues": job.critical_issues_count,
                "warnings": job.warning_issues_count,
                "pages_discovered": job.pages_discovered,
                "pages_selected": job.pages_selected,
                "pages_analyzed": job.pages_llm_analyzed,
                "issues": all_issues
            }
        }

        parsed_result = parse_audit_report(unparsed_result)

        return api_response(
            data=parsed_result
        )

    except Exception as e:
        logger.error(f"Error fetching scan results: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching scan results: {str(e)}",
            data={}
        )


@router.get("/{job_id}/issues")
async def get_scan_issues(job_id: str, db: AsyncSession = Depends(get_db)):

    try:
        job = await db.scalar(select(ScanJob).where(ScanJob.id == job_id))
        if not job:
            return api_response(status_code=404, message="Scan job not found")

        if job.status != ScanJobStatus.completed:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Scan is not completed yet. Current status: {job.status.value}",
                data={"status": job.status.value}
            )

        issues = await db.scalars(
            select(ScanIssue).where(ScanIssue.scan_job_id == job_id)
        )

        score_overall = job.score_overall or 0
        parsed_issues = parse_detailed_audit_report({
                "job_id": job_id,
                "status": job.status,
                "scanned_at": job.completed_at,
                "score_overall": score_overall,
                "score_seo": job.score_seo or 0,
                "score_accessibility": job.score_accessibility or 0,
                "score_performance": job.score_performance or 0,
                "summary": generate_summary_message(score_overall),
                "issues": [
                    {
                        "id": issue.id,
                        "scan_page_id": issue.scan_page_id,
                        "scan_job_id": issue.scan_job_id,
                        "category": issue.category.value,
                        "severity": issue.severity.value,
                        "title": issue.title,
                        "description": issue.description,
                        "recommendation": issue.recommendation,
                        "business_impact": issue.business_impact,
                        "created_at": issue.created_at,
                    }
                    for issue in issues
                ]
            })
        return api_response(
            data=parsed_issues
        )

    except Exception as e:
        logger.error(f"Error fetching scan issues: {e}")
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching scan issues: {str(e)}",
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
            pages_query = pages_query.where(
                ScanPage.is_selected_by_llm == True)

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


@router.post("/{job_id}/stop")
async def stop_scan(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    success = await stop_scan_job(job_id, db)
    if not success:
        return api_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"Scan job {job_id} not found",
            data={}
        )
    return api_response(
        data={"job_id": job_id, "status": "cancelled"},
        message="Scan stopped successfully",
        status_code=status.HTTP_200_OK
    )

@router.delete(
    "/{job_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an individual scan job",
    description="""
    Task 3: Delete a specific scan job record.
    
    This endpoint:
    1. Verifies the scan job belongs to the authenticated user
    2. Deletes the scan job and its related records (pages, issues) efficiently
    
    Path Parameters:
    - job_id: The unique identifier of the scan job to delete 
    
    Returns:
    - 204: Scan deleted successfully
    - 404: Scan not found or doesn't belong to the user
    - 500: Server error during deletion
    """
)
async def delete_scan(
    job_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an individual scan record.
    """
    try:
        scan_result = await db.execute(
            select(ScanJob).where(
                ScanJob.id == job_id,
                ScanJob.user_id == current_user.id,
            )
        )
        scan = scan_result.scalar_one_or_none()
        if not scan:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Scan not found or not owned by user",
                data={}
            )

        await db.delete(scan)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting scan {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting scan"
        )