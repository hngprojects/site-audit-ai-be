import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from celery import shared_task, chain, group, chord
from celery.exceptions import Retry

from app.platform.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_sync_db():
    """Get a database session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.platform.config import settings
    
    # Convert async URL to sync if needed
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def update_job_status(job_id: str, status, **kwargs):
    """Update scan job status in database. Status can be string or ScanJobStatus enum."""
    # Import all related models to ensure SQLAlchemy mappers are configured
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
    from app.features.scan.models.scan_page import ScanPage  # noqa: F401
    
    db = get_sync_db()
    try:
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if job:
            job.status = status
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            db.commit()
    finally:
        db.close()


# Phase 1: Discovery

@celery_app.task(
    bind=True,
    name="app.features.scan.workers.tasks.discover_pages",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def discover_pages(
    self,
    job_id: str,
    url: str,
    max_pages: int = 100
) -> Dict[str, Any]:
    """
    Discover all pages on a website.
    
    Args:
        job_id: The scan job ID
        url: Root URL to crawl
        max_pages: Maximum pages to discover
        
    Returns:
        Dict with discovered pages and metadata
    """
    from app.features.scan.services.discovery.page_discovery import PageDiscoveryService
    
    logger.info(f"[{job_id}] Starting page discovery for {url}")
    from app.features.scan.models.scan_job import ScanJobStatus
    update_job_status(job_id, ScanJobStatus.discovering, started_at=datetime.utcnow())
    
    try:
        discovery_service = PageDiscoveryService()
        pages = discovery_service.discover_pages(url=url, max_pages=max_pages)
        
        # Store discovered pages in DB
        _save_discovered_pages(job_id, pages)
        
        update_job_status(job_id, ScanJobStatus.discovering, pages_discovered=len(pages))
        
        logger.info(f"[{job_id}] Discovered {len(pages)} pages")
        return {
            "job_id": job_id,
            "pages": pages,
            "count": len(pages),
            "url": url
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Discovery failed: {e}")
        update_job_status(job_id, ScanJobStatus.failed, error_message=str(e))
        raise


def _save_discovered_pages(job_id: str, pages: List[str]):
    """Save discovered pages to database."""
    # Import all related models to ensure SQLAlchemy mappers are configured
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob  # noqa: F401
    from app.features.scan.models.scan_page import ScanPage
    
    db = get_sync_db()
    try:
        for page_url in pages:
            page = ScanPage(
                scan_job_id=job_id,
                page_url=page_url,
                page_url_normalized=page_url.rstrip('/'),
                is_selected_by_llm=False,
                is_manually_selected=False,
                is_manually_deselected=False
            )
            db.add(page)
        db.commit()
    finally:
        db.close()



# Phase 2: Selection

@celery_app.task(
    bind=True,
    name="app.features.scan.workers.tasks.select_pages",
    max_retries=3,
    default_retry_delay=10
)
def select_pages(
    self,
    discovery_result: Dict[str, Any],
    top_n: int = 15,
    referer: str = "",
    site_title: str = ""
) -> Dict[str, Any]:
    """
    Select important pages using LLM.
    
    Args:
        discovery_result: Output from discover_pages task
        top_n: Maximum pages to select
        referer: HTTP referer for LLM API
        site_title: Site title for LLM API
        
    Returns:
        Dict with selected pages
    """
    from app.features.scan.services.analysis.page_selector import PageSelectorService
    
    job_id = discovery_result["job_id"]
    pages = discovery_result["pages"]
    
    logger.info(f"[{job_id}] Selecting important pages from {len(pages)} discovered")
    from app.features.scan.models.scan_job import ScanJobStatus
    update_job_status(job_id, ScanJobStatus.selecting)
    
    try:
        selector = PageSelectorService()
        selected = selector.filter_important_pages(
            pages=pages,
            top_n=top_n,
            referer=referer,
            site_title=site_title
        )
        
        # Update pages in DB
        _mark_selected_pages(job_id, selected)
        
        update_job_status(job_id, ScanJobStatus.selecting, pages_selected=len(selected))
        
        logger.info(f"[{job_id}] Selected {len(selected)} pages for analysis")
        return {
            "job_id": job_id,
            "selected_pages": selected,
            "count": len(selected),
            "total_discovered": len(pages)
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Selection failed: {e}")
        update_job_status(job_id, ScanJobStatus.failed, error_message=str(e))
        raise


def _mark_selected_pages(job_id: str, selected_urls: List[str]):
    """Mark selected pages in database."""
    # Import all related models to ensure SQLAlchemy mappers are configured
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob  # noqa: F401
    from app.features.scan.models.scan_page import ScanPage
    
    db = get_sync_db()
    try:
        selected_normalized = {url.rstrip('/') for url in selected_urls}
        pages = db.query(ScanPage).filter(ScanPage.scan_job_id == job_id).all()
        
        for page in pages:
            if page.page_url_normalized in selected_normalized:
                page.is_selected_by_llm = True
        
        db.commit()
    finally:
        db.close()


# =============================================================================
# Phase 3: Scraping (per-page)
# =============================================================================

@celery_app.task(
    bind=True,
    name="app.features.scan.workers.tasks.scrape_page",
    max_retries=3,
    default_retry_delay=5
)
def scrape_page(
    self,
    job_id: str,
    page_url: str,
    page_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scrape and extract comprehensive data for a single page using Selenium.
    
    Extracts:
    - Metadata (title, description, meta tags)
    - Headings hierarchy (h1-h6)
    - Images (src, alt, dimensions)
    - Links (internal, external)
    - Performance metrics (TTFB, load time)
    - Accessibility features (ARIA, semantic HTML)
    - Design signals (colors, fonts, spacing)
    - Text content (word count, readability)
    
    Args:
        job_id: The scan job ID
        page_url: URL to scrape
        page_id: Optional page record ID
        
    Returns:
        Dict with comprehensive scraped data
    """
    from app.features.scan.services.scraping import ScrapingService
    
    logger.info(f"[{job_id}] Scraping page: {page_url}")
    
    try:
        # Initialize scraping service
        scraper = ScrapingService(headless=True, timeout=30)
        
        # Scrape page and extract all data
        report = scraper.scrape_page(page_url)
        
        # Store scraped data in database if page_id provided
        if page_id:
            _store_scraped_data(page_id, report)
        
        logger.info(f"[{job_id}] Successfully scraped {page_url}")
        
        return {
            "job_id": job_id,
            "page_id": page_id,
            "page_url": page_url,
            "report": report,
            "http_status": 200,
            "scraped_at": report.get("scraped_at")
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Scraping failed for {page_url}: {e}")
        
        # Store error in database if page_id provided
        if page_id:
            _store_scraping_error(page_id, str(e))
        
        raise


def _store_scraped_data(page_id: str, report: Dict[str, Any]):
    """Store comprehensive scraped data in ScanPage record."""
    # Import all related models
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob  # noqa: F401
    from app.features.scan.models.scan_page import ScanPage
    
    db = get_sync_db()
    try:
        page = db.query(ScanPage).filter(ScanPage.id == page_id).first()
        if page:
            # Store metadata
            metadata = report.get("metadata", {})
            page.page_title = metadata.get("title", "")[:512]
            
            # Store performance metrics
            performance = report.get("performance", {})
            page.ttfb_ms = performance.get("ttfb_ms")
            page.load_time_ms = performance.get("page_load_ms")
            
            # Store HTTP status
            page.http_status = 200
            
            # Store scraped timestamp
            page.scanned_at = datetime.utcnow()
            
            # TODO: Store full report as JSON in scan_results_path or separate field
            # For now, we'll let the extraction and analysis phases use this data
            
            db.commit()
            logger.info(f"Stored scraped data for page {page_id}")
    except Exception as e:
        logger.error(f"Error storing scraped data for page {page_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _store_scraping_error(page_id: str, error_message: str):
    """Store scraping error in ScanPage record."""
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob  # noqa: F401
    from app.features.scan.models.scan_page import ScanPage
    
    db = get_sync_db()
    try:
        page = db.query(ScanPage).filter(ScanPage.id == page_id).first()
        if page:
            page.http_status = 500
            # Store error in a field if available, or log it
            db.commit()
    except Exception as e:
        logger.error(f"Error storing scraping error for page {page_id}: {e}")
    finally:
        db.close()


# =============================================================================
# Phase 4: Extraction (per-page)
# =============================================================================

@celery_app.task(
    bind=True,
    name="app.features.scan.workers.tasks.extract_data",
    max_retries=2,
    default_retry_delay=5
)
def extract_data(
    self,
    scrape_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Extract structured data from scraped HTML.
    
    This is a placeholder - integrate extraction service here.
    
    Args:
        scrape_result: Output from scrape_page task
        
    Returns:
        Dict with extracted data
    """
    job_id = scrape_result["job_id"]
    page_url = scrape_result["page_url"]
    
    logger.info(f"[{job_id}] Extracting data from: {page_url}")
    
    try:
        # TODO: extraction service here
        # For now, return placeholder
        extracted = {
            "title": "Placeholder Title",
            "meta_description": "Placeholder description",
            "h1_tags": [],
            "images": [],
            "links": []
        }
        
        return {
            "job_id": job_id,
            "page_id": scrape_result.get("page_id"),
            "page_url": page_url,
            "extracted_data": extracted
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Extraction failed for {page_url}: {e}")
        raise


# =============================================================================
# Phase 5: Analysis (per-page, LLM)
# =============================================================================

@celery_app.task(
    bind=True,
    name="app.features.scan.workers.tasks.analyze_page",
    max_retries=3,
    default_retry_delay=10
)
def analyze_page(
    self,
    extraction_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze a page using LLM for SEO, accessibility, etc.
    
    This is a placeholder - team will integrate their analysis service here.
    
    Args:
        extraction_result: Output from extract_data task
        
    Returns:
        Dict with analysis results and scores
    """
    job_id = extraction_result["job_id"]
    page_url = extraction_result["page_url"]
    
    logger.info(f"[{job_id}] Analyzing page: {page_url}")
    
    try:
        # TODO: Team integrates their LLM analysis service here
        # For now, return placeholder scores
        analysis = {
            "score_overall": 75,
            "score_seo": 80,
            "score_accessibility": 70,
            "score_performance": 75,
            "score_design": 72,
            "issues": []
        }
        
        # Update page record with scores
        _update_page_scores(
            extraction_result.get("page_id"),
            analysis
        )
        
        return {
            "job_id": job_id,
            "page_id": extraction_result.get("page_id"),
            "page_url": page_url,
            "analysis": analysis
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Analysis failed for {page_url}: {e}")
        raise


def _update_page_scores(page_id: Optional[str], analysis: Dict):
    """Update page scores in database."""
    if not page_id:
        return
    
    # Import all related models to ensure SQLAlchemy mappers are configured
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob  # noqa: F401
    from app.features.scan.models.scan_page import ScanPage
    
    db = get_sync_db()
    try:
        page = db.query(ScanPage).filter(ScanPage.id == page_id).first()
        if page:
            page.score_overall = analysis.get("score_overall")
            page.score_seo = analysis.get("score_seo")
            page.score_accessibility = analysis.get("score_accessibility")
            page.score_performance = analysis.get("score_performance")
            page.score_design = analysis.get("score_design")
            page.scanned_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


# =============================================================================
# Phase 6: Aggregation
# =============================================================================

@celery_app.task(
    bind=True,
    name="app.features.scan.workers.tasks.aggregate_results"
)
def aggregate_results(
    self,
    analysis_results: List[Dict[str, Any]],
    job_id: str
) -> Dict[str, Any]:
    """
    Aggregate all page analysis results into final scores.
    
    Args:
        analysis_results: List of outputs from analyze_page tasks
        job_id: The scan job ID
        
    Returns:
        Dict with aggregated scores and summary
    """
    logger.info(f"[{job_id}] Aggregating results from {len(analysis_results)} pages")
    
    try:
        # Calculate average scores
        if not analysis_results:
            aggregated = {
                "score_overall": 0,
                "score_seo": 0,
                "score_accessibility": 0,
                "score_performance": 0,
                "score_design": 0,
                "total_issues": 0
            }
        else:
            valid_results = [r for r in analysis_results if r.get("analysis")]
            count = len(valid_results)
            
            aggregated = {
                "score_overall": sum(r["analysis"]["score_overall"] for r in valid_results) // count if count else 0,
                "score_seo": sum(r["analysis"]["score_seo"] for r in valid_results) // count if count else 0,
                "score_accessibility": sum(r["analysis"]["score_accessibility"] for r in valid_results) // count if count else 0,
                "score_performance": sum(r["analysis"]["score_performance"] for r in valid_results) // count if count else 0,
                "score_design": sum(r["analysis"]["score_design"] for r in valid_results) // count if count else 0,
                "total_issues": sum(len(r["analysis"].get("issues", [])) for r in valid_results),
                "pages_analyzed": count
            }
        
        # Update job with final scores
        _update_job_final_scores(job_id, aggregated)
        
        logger.info(f"[{job_id}] Scan completed with overall score: {aggregated['score_overall']}")
        
        return {
            "job_id": job_id,
            "status": "completed",
            "scores": aggregated
        }
        
    except Exception as e:
        logger.error(f"[{job_id}] Aggregation failed: {e}")
        update_job_status(job_id, "failed", error_message=str(e))
        raise


def _update_job_final_scores(job_id: str, scores: Dict):
    """Update job with final aggregated scores."""
    # Import all related models to ensure SQLAlchemy mappers are configured
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob
    from app.features.scan.models.scan_page import ScanPage  # noqa: F401
    
    db = get_sync_db()
    try:
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if job:
            job.status = "completed"
            job.score_overall = scores.get("score_overall")
            job.score_seo = scores.get("score_seo")
            job.score_accessibility = scores.get("score_accessibility")
            job.score_performance = scores.get("score_performance")
            job.score_design = scores.get("score_design")
            job.total_issues = scores.get("total_issues", 0)
            job.pages_llm_analyzed = scores.get("pages_analyzed", 0)
            job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


# =============================================================================
# Pipeline Orchestrator
# =============================================================================

@celery_app.task(
    bind=True,
    name="app.features.scan.workers.tasks.run_scan_pipeline"
)
def run_scan_pipeline(
    self,
    job_id: str,
    url: str,
    top_n: int = 15,
    max_pages: int = 100
) -> str:
    """
    Orchestrate the full scan pipeline.
    
    Creates a Celery workflow that chains:
    1. Discovery -> 2. Selection -> 3. [Scrape -> Extract -> Analyze] for each page -> 4. Aggregate
    
    Args:
        job_id: The scan job ID
        url: Root URL to scan
        top_n: Max pages to select
        max_pages: Max pages to discover
        
    Returns:
        Job ID for tracking
    """
    logger.info(f"[{job_id}] Starting scan pipeline for {url}")
    
    # Chain: Discovery -> Selection
    # Then fan-out to process each page in parallel
    # Finally aggregate results
    
    workflow = chain(
        discover_pages.s(job_id, url, max_pages),
        select_pages.s(top_n=top_n, referer=url, site_title=""),
        process_selected_pages.s(job_id)
    )
    
    workflow.apply_async()
    
    return job_id


@celery_app.task(
    bind=True,
    name="app.features.scan.workers.tasks.process_selected_pages"
)
def process_selected_pages(
    self,
    selection_result: Dict[str, Any],
    job_id: str
) -> Dict[str, Any]:
    """
    Process all selected pages in parallel, then aggregate.
    
    Creates a chord: parallel page processing -> aggregation
    """
    selected_pages = selection_result.get("selected_pages", [])
    
    if not selected_pages:
        logger.warning(f"[{job_id}] No pages selected for processing")
        return aggregate_results.delay([], job_id)
    
    from app.features.scan.models.scan_job import ScanJobStatus
    update_job_status(job_id, ScanJobStatus.scraping)
    
    # Create parallel tasks for each page
    page_tasks = []
    for page_url in selected_pages:
        # Chain: scrape -> extract -> analyze for each page
        page_workflow = chain(
            scrape_page.s(job_id, page_url),
            extract_data.s(),
            analyze_page.s()
        )
        page_tasks.append(page_workflow)
    
    # Chord: run all page tasks in parallel, then aggregate
    workflow = chord(page_tasks)(aggregate_results.s(job_id))
    
    return {"job_id": job_id, "pages_queued": len(selected_pages)}
