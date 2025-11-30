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
    max_pages: int = 1
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
    update_job_status(job_id, ScanJobStatus.discovering,
                      started_at=datetime.utcnow())

    try:
        discovery_service = PageDiscoveryService()
        pages = discovery_service.discover_pages(url=url, max_pages=max_pages)

        # Store discovered pages in DB
        _save_discovered_pages(job_id, pages)

        update_job_status(job_id, ScanJobStatus.discovering,
                          pages_discovered=len(pages))

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


def _update_page_scrape_data(page_id: str, html_content: str, page_title: Optional[str], content_length: int):
    """Update page record with scraped data."""
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob  # noqa: F401
    from app.features.scan.models.scan_page import ScanPage
    import hashlib

    db = get_sync_db()
    try:
        page = db.query(ScanPage).filter(ScanPage.id == page_id).first()
        if page:
            page.page_title = page_title
            page.content_length_bytes = content_length
            page.http_status = 200

            # Generate content hash for caching
            if html_content:
                content_hash = hashlib.sha256(
                    html_content.encode('utf-8')).hexdigest()
                page.content_hash_current = content_hash

            db.commit()
    finally:
        db.close()


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
    top_n: int = 5,
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

    logger.info(
        f"[{job_id}] Selecting important pages from {len(pages)} discovered")
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

        update_job_status(job_id, ScanJobStatus.selecting,
                          pages_selected=len(selected))

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


def _get_page_ids_for_urls(job_id: str, urls: List[str]) -> Dict[str, str]:
    """Get page IDs for given URLs from database."""
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob  # noqa: F401
    from app.features.scan.models.scan_page import ScanPage

    db = get_sync_db()
    try:
        url_normalized = {url.rstrip('/') for url in urls}
        pages = db.query(ScanPage).filter(
            ScanPage.scan_job_id == job_id,
            ScanPage.page_url_normalized.in_(url_normalized)
        ).all()

        # Map normalized URL to page ID
        return {page.page_url: str(page.id) for page in pages}
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
    Scrape HTML content for a single page using ScrapingService.
    Returns serializable data that can be passed to extract_data task.

    Args:
        job_id: The scan job ID
        page_url: URL to scrape
        page_id: Optional page record ID

    Returns:
        Dict with scraped HTML and metadata (fully serializable)
    """
    from app.features.scan.services.scraping.scraping_service import ScrapingService

    logger.info(f"[{job_id}] Scraping page: {page_url}")

    try:
        # Use improved scrape_page method that returns serializable data
        scrape_result = ScrapingService.scrape_page(page_url, timeout=15)

        if not scrape_result["success"]:
            logger.error(
                f"[{job_id}] Scraping failed for {page_url}: {scrape_result.get('error')}")
            raise Exception(scrape_result.get(
                "error", "Unknown scraping error"))

        # Store basic scraping info in database
        if page_id and scrape_result["html"]:
            _update_page_scrape_data(
                page_id,
                scrape_result["html"],
                scrape_result["page_title"],
                scrape_result["content_length"]
            )

        result = {
            "job_id": job_id,
            "page_id": page_id,
            "page_url": page_url,
            "html": scrape_result["html"],
            "page_title": scrape_result["page_title"],
            "content_length": scrape_result["content_length"],
            "current_url": scrape_result.get("current_url", page_url)
        }

        logger.info(
            f"[{job_id}] Successfully scraped {page_url} ({scrape_result['content_length']} bytes)")
        return result

    except Exception as e:
        logger.error(f"[{job_id}] Scraping failed for {page_url}: {e}")
        raise


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
    Extract structured data from scraped HTML using ExtractorService.

    Args:
        scrape_result: Output from scrape_page task containing HTML

    Returns:
        Dict with extracted data
    """
    from app.features.scan.services.extraction.extractor_service import ExtractorService

    job_id = scrape_result["job_id"]
    page_url = scrape_result["page_url"]
    page_id = scrape_result.get("page_id")
    html = scrape_result.get("html")

    logger.info(f"[{job_id}] Extracting data from: {page_url}")

    try:
        if not html:
            raise ValueError("No HTML content provided in scrape_result")

        # Extract all data using ExtractorService.extract_from_html
        extracted = ExtractorService.extract_from_html(html, page_url)

        # Update database with extracted data
        if page_id:
            _update_page_extracted_data(page_id, extracted)

        result = {
            "job_id": job_id,
            "page_id": page_id,
            "page_url": page_url,
            "extracted_data": extracted
        }

        logger.info(f"[{job_id}] Successfully extracted data from {page_url}")
        return result

    except Exception as e:
        logger.error(f"[{job_id}] Extraction failed for {page_url}: {e}")
        raise


def _update_page_extracted_data(page_id: str, extracted: Dict):
    """Update page record with extracted data for later analysis."""
    from app.features.auth.models.user import User  # noqa: F401
    from app.features.sites.models.site import Site  # noqa: F401
    from app.features.scan.models.scan_job import ScanJob  # noqa: F401
    from app.features.scan.models.scan_page import ScanPage

    db = get_sync_db()
    try:
        page = db.query(ScanPage).filter(ScanPage.id == page_id).first()
        if page:
            # Update page title if extracted from metadata
            metadata = extracted.get("metadata", {})
            if metadata.get("title"):
                page.page_title = metadata["title"]

            # Count issues from accessibility and metadata
            accessibility = extracted.get("accessibility", {})
            metadata_issues = len(metadata.get("issues", []))

            # Count accessibility issues
            accessibility_issues = sum([
                len(accessibility.get("images_missing_alt", [])),
                len(accessibility.get("inputs_missing_label", [])),
                len(accessibility.get("buttons_missing_label", [])),
                len(accessibility.get("links_missing_label", [])),
                len(accessibility.get("empty_headings", []))
            ])

            # Classify issues
            page.critical_issues_count = metadata_issues  # Metadata issues are critical
            # Accessibility issues are warnings
            page.warning_issues_count = accessibility_issues

            db.commit()
    finally:
        db.close()

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
    extraction_result: Dict[str, Any],
    job_id: str
) -> Dict[str, Any]:

    from app.features.scan.services.analysis.page_analyzer import PageAnalyzerService
    from app.features.scan.models.scan_job import ScanJobStatus

    # Extract metadata from the extraction result
    page_url = extraction_result.get("page_url")
    page_id = extraction_result.get("page_id")

    # Get the extracted data in the format PageAnalyzerService expects
    extracted_data = extraction_result.get("extracted_data", {})

    # Update status to analyzing when first analysis task starts
    update_job_status(job_id, ScanJobStatus.analyzing)

    logger.info(f"[{job_id}] Analyzing page: {page_url}")

    try:
        # Pass extracted_data which has the format: {status_code, status, message, data}
        analysis_result = PageAnalyzerService.analyze_page(extracted_data)

        analysis = _transform_analysis_result(analysis_result)

        _update_page_analysis(page_id, analysis, analysis_result)

        logger.info(
            f"[{job_id}] Analysis complete for {page_url}: {analysis['overall_score']}/100"
        )

        return {
            "job_id": job_id,
            "page_id": page_id,
            "page_url": page_url,
            "analysis": analysis,
            "detailed_analysis": analysis_result
        }

    except Exception as e:
        logger.error(
            f"[{job_id}] Analysis failed for {page_url}: {e}",
            exc_info=True
        )
        self.retry(exc=e)


def _transform_analysis_result(analysis_result) -> Dict[str, Any]:
    """
    Transform PageAnalysisResult dict to database-friendly format.
    Maps LLM output (Usability/Performance/SEO) to database fields (Accessibility/Design/Performance/SEO).

    Args:
        analysis_result: Dict from PageAnalyzerService with nested structure:
            {overall_score, usability: {score, ...}, performance: {score, ...}, seo: {score, ...}}

    Returns:
        Dict with flat structure for database storage
    """
    usability = analysis_result.get("usability", {})
    performance = analysis_result.get("performance", {})
    seo = analysis_result.get("seo", {})

    return {
        "overall_score": analysis_result.get("overall_score"),
        "score_accessibility": usability.get("score"),
        "score_performance": performance.get("score"),
        "score_seo": seo.get("score"),
    }


def _map_icon_to_severity(icon: str) -> str:
    """
    Map problem icon from LLM response to severity level.

    Args:
        icon: Icon string from LLM ('alert' or 'warning')

    Returns:
        Severity level string
    """
    if icon == "alert":
        return "high"
    elif icon == "warning":
        return "medium"
    else:
        return "low"


def _create_scan_issues(
    page_id: str,
    job_id: str,
    detailed_analysis: Dict[str, Any]
) -> int:
    """
    Extract problems from detailed_analysis and create ScanIssue records.

    Args:
        page_id: Database ID of the scanned page
        job_id: Database ID of the scan job
        detailed_analysis: Full structured analysis result from LLM

    Returns:
        Number of issues created
    """
    from app.features.scan.models.scan_issue import ScanIssue, IssueCategory, IssueSeverity

    db = get_sync_db()
    issues_created = 0

    try:
        # Extract problems from each category
        categories_map = {
            # Usability problems map to accessibility
            "usability": IssueCategory.accessibility,
            "performance": IssueCategory.performance,
            "seo": IssueCategory.seo,
        }

        for section_key, issue_category in categories_map.items():
            section = detailed_analysis.get(section_key, {})
            problems = section.get("problems", [])

            for problem in problems:
                try:
                    # Extract problem details
                    icon = problem.get("icon", "warning")
                    title = problem.get("title", "")
                    # Fallback to title if no description
                    description = problem.get("description", title)

                    # Skip if no title
                    if not title:
                        logger.warning(
                            f"Skipping problem with no title in {section_key} section")
                        continue

                    # Map icon to severity
                    severity_str = _map_icon_to_severity(icon)

                    # Create ScanIssue record
                    issue = ScanIssue(
                        scan_page_id=page_id,
                        scan_job_id=job_id,
                        category=issue_category,
                        severity=IssueSeverity[severity_str],
                        title=title[:512],  # Truncate to column limit
                        description=description,
                        what_this_means=None,  # Not provided by current LLM response
                        recommendation=None,  # Not provided by current LLM response
                        element_selector=None,  # Not provided by current LLM response
                        element_html=None,  # Not provided by current LLM response
                    )

                    db.add(issue)
                    issues_created += 1

                except Exception as e:
                    logger.error(
                        f"Failed to create issue from problem: {e}", exc_info=True)
                    continue

        # Commit all issues at once
        db.commit()
        logger.info(
            f"Created {issues_created} ScanIssue records for page {page_id}")

    except Exception as e:
        logger.error(f"Failed to create scan issues: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

    return issues_created


def _update_page_analysis(
    page_id: Optional[str],
    analysis: Dict[str, Any],
    detailed_analysis: Dict[str, Any]
) -> None:
    """
    Update page analysis results in database.

    Args:
        page_id: Database ID of the page
        analysis: Flat analysis scores
        detailed_analysis: Full structured analysis result
    """
    if not page_id:
        logger.warning("No page_id provided, skipping database update")
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
            page.score_overall = analysis.get("overall_score")
            page.score_accessibility = analysis.get("score_accessibility")
            page.score_performance = analysis.get("score_performance")
            page.score_seo = analysis.get("score_seo")

            # Store detailed analysis as JSON if column exists
            if hasattr(page, 'analysis_details'):
                page.analysis_details = detailed_analysis
                logger.info(f"Stored detailed_analysis for page {page_id}")
            else:
                logger.warning(
                    f"Page model missing 'analysis_details' column - detailed analysis not saved")

            page.scanned_at = datetime.utcnow()
            db.commit()

            logger.info(f"Updated page {page_id} with analysis scores")

            # Create individual ScanIssue records from problems in detailed_analysis
            try:
                # Get job_id from the page object
                job_id = page.scan_job_id
                issues_count = _create_scan_issues(
                    page_id, job_id, detailed_analysis)
                logger.info(
                    f"Created {issues_count} issues for page {page_id}")
            except Exception as e:
                logger.error(
                    f"Failed to create scan issues for page {page_id}: {e}", exc_info=True)
                # Don't fail the whole analysis if issue creation fails
        else:
            logger.warning(f"Page {page_id} not found in database")

    except Exception as e:
        logger.error(f"Failed to update page analysis: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def _update_page_scores(page_id: Optional[str], analysis: Dict):
    """Update page scores in database (deprecated - use _update_page_analysis instead)."""
    if not page_id:
        logger.warning("No page_id provided, skipping database update")
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
            page.score_overall = analysis.get("overall_score")
            page.score_accessibility = analysis.get("score_accessibility")
            page.score_performance = analysis.get("score_performance")
            page.score_seo = analysis.get("score_seo")

            page.scanned_at = datetime.utcnow()
            db.commit()

            logger.info(f"Updated page {page_id} with analysis scores")
        else:
            logger.warning(f"Page {page_id} not found in database")

    except Exception as e:
        logger.error(f"Failed to update page analysis: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# Phase 6: Aggregation
# =============================================================================

def _count_scan_issues(job_id: str) -> int:
    """
    Count total number of ScanIssue records for a job.

    Args:
        job_id: Database ID of the scan job

    Returns:
        Total count of issues
    """
    from app.features.scan.models.scan_issue import ScanIssue

    db = get_sync_db()
    try:
        count = db.query(ScanIssue).filter(
            ScanIssue.scan_job_id == job_id).count()
        logger.info(f"Found {count} total issues for job {job_id}")
        return count
    except Exception as e:
        logger.error(f"Failed to count scan issues: {e}", exc_info=True)
        return 0
    finally:
        db.close()


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
    logger.info(
        f"[{job_id}] Aggregating results from {len(analysis_results)} pages")

    try:
        # Calculate average scores
        if not analysis_results:
            aggregated = {
                "score_overall": 0,
                "score_seo": 0,
                "score_accessibility": 0,
                "score_performance": 0,
                "total_issues": 0
            }
        else:
            valid_results = [r for r in analysis_results if r.get("analysis")]
            count = len(valid_results)

            aggregated = {
                "score_overall": sum(r["analysis"].get("overall_score", 0) for r in valid_results) // count if count else 0,
                "score_seo": sum(r["analysis"].get("score_seo", 0) for r in valid_results) // count if count else 0,
                "score_accessibility": sum(r["analysis"].get("score_accessibility", 0) for r in valid_results) // count if count else 0,
                "score_performance": sum(r["analysis"].get("score_performance", 0) for r in valid_results) // count if count else 0,
                "total_issues": _count_scan_issues(job_id),
                "pages_analyzed": count
            }

        # Update job with final scores
        _update_job_final_scores(job_id, aggregated)

        logger.info(
            f"[{job_id}] Scan completed with overall score: {aggregated['score_overall']}")

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
    top_n: int = 5,
    max_pages: int = 1,
    notification_email: Optional[str] = None,
    user_name: Optional[str] = None
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
        notification_email: Optional email to notify on completion
        user_name: Optional user name for email personalization

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
        process_selected_pages.s(job_id, notification_email, user_name),
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
    job_id: str,
    notification_email: Optional[str] = None,
    user_name: Optional[str] = None
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

    # Get page IDs from database for tracking
    page_id_map = _get_page_ids_for_urls(job_id, selected_pages)

    # Create parallel tasks for each page
    page_tasks = []
    for page_url in selected_pages:
        page_id = page_id_map.get(page_url)
        # Chain: scrape -> extract -> analyze for each page
        page_workflow = chain(
            scrape_page.s(job_id, page_url, page_id),
            extract_data.s(),
            analyze_page.s(job_id)
        )
        page_tasks.append(page_workflow)

    # Chord: run all page tasks in parallel, then aggregate
    # If notification email is provided, chain it after aggregation
    aggregation_task = aggregate_results.s(job_id)
    
    if notification_email:
        from app.features.scan.workers.periodic_tasks import send_scan_completion_email
        # Chain: aggregation -> send_email
        # Note: send_scan_completion_email takes (job_id, user_email, user_name, site_name)
        # But here we're chaining, so it receives the result of aggregate_results as first arg
        # We need to ignore that result or handle it. 
        # Better approach: Use a callback that takes the result and calls the email task
        
        # Since send_scan_completion_email is a Celery task, we can chain it.
        # However, aggregate_results returns a dict. send_scan_completion_email expects arguments.
        # We'll use an immutable signature (.si) to ignore the previous result and pass explicit args
        
        # We need site_name. We can get it from the job or pass it down. 
        # For simplicity, let's pass "Your Site" or fetch it in the email task.
        # The email task already fetches the job, so it can get the site name if we pass job_id.
        
        # Let's update send_scan_completion_email to be more flexible or just pass arguments here.
        # We'll pass site_name="Your Site" for now, or fetch it.
        
        final_workflow = chain(
            aggregation_task,
            send_scan_completion_email.si(
                job_id=job_id, 
                user_email=notification_email, 
                user_name=user_name or "User",
                site_name="Your Site" # The task can fetch the real name if needed
            )
        )
        workflow = chord(page_tasks)(final_workflow)
    else:
        workflow = chord(page_tasks)(aggregation_task)

    return {"job_id": job_id, "pages_queued": len(selected_pages)}
