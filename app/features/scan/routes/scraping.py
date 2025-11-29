from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.scan.schemas.scan import ScrapingRequest, ScrapingResponse
from app.features.scan.services.scraping.scraping_service import ScrapingService
from app.features.scan.services.extraction.extractor_service import ExtractorService
from app.features.scan.models.scan_page import ScanPage
from app.platform.response import api_response

from app.platform.db.session import get_db
import hashlib

router = APIRouter(prefix="/scan/scraping", tags=["scan-scraping"])


@router.get("/extract-test")
async def test_extraction(
    url: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Test endpoint to extract data from any URL.
    
    This is a testing/debugging endpoint that extracts data from a URL
    and returns the full extraction result without storing it in the database.
    
    Args:
        url: URL to extract data from
        db: Database session
        
    Returns:
        Complete extracted data structure with all fields
        
    Example:
        GET /scan/scraping/extract-test?url=https://example.com
    """
    try:
        scraper = None
        driver = None

        try:
            page_url = str(url)
            # Initialize scraping service
            scraper = ScrapingService(headless=True, timeout=30)
            driver = scraper.load_page(page_url)

            # Use the unified extract_from_html method
            # First get the HTML
            html = driver.page_source
            
            # Extract all data using the standardized method
            extracted_data = ExtractorService.extract_from_html(html, page_url)
            
            # Add HTML preview for debugging
            response_data = extracted_data
            if isinstance(response_data, dict):
                response_data["debug_html_preview"] = html[:1000]  # First 1000 chars
                response_data["debug_html_length"] = len(html)
            
            return api_response(
                message=f"Successfully extracted data from {page_url}",
                data=response_data
            )
        except Exception as e:
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Extraction failed: {str(e)}",
                data={}
            )
        finally:
            if driver:
                driver.quit()
            
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Test extraction failed: {str(e)}",
            data={}
        )


@router.post("", response_model=ScrapingResponse)
async def scrape_pages(
    data: ScrapingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scrape selected pages using Selenium and extract comprehensive data.
    
    This endpoint:
    - Takes selected pages from the request
    - Uses Selenium to scrape full page content
    - Extracts metadata, headings, images, links, performance metrics,
      accessibility features, design signals, and text content
    - Returns comprehensive scraping data
    
    Called by: Scraping worker after selection completes
    
    Args:
        data: ScrapingRequest with pages to scrape
        db: Database session
        
    Returns:
        ScrapingResponse with scraped page data
    """
    try:
        # Scrape all pages using static method
        scraped_pages = []
        for page_url in data.pages:
            try:
                result = ScrapingService.scrape_page(page_url, timeout=30)
                scraped_pages.append(result)
            except Exception as e:
                # Log error but continue with other pages
                scraped_pages.append({
                    "url": page_url,
                    "success": False,
                    "error": str(e)
                })
        
        
        # TODO: Store scraped data in ScanPage records
        # - Save HTML content, metadata, and extracted data
        # - Update ScanJob scraping_status to 'completed'
        # - Calculate and store page scores
        
        return api_response(
            data={
                "scraped_pages": scraped_pages,
                "count": len(scraped_pages),
                "job_id": data.job_id,
                "message": f"Successfully scraped {len(scraped_pages)} pages"
            }
        )
            
    except Exception as e:
        # Log the full error with traceback
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Scraping failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # TODO: If job_id provided, mark scraping_status = 'failed'
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Scraping failed: {str(e)}",
            data={"error": str(e), "traceback": traceback.format_exc()}
        )


@router.get("/page/{page_id}/extracted-data")
async def get_page_extracted_data(
    page_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get extracted data for a specific page.
    
    This endpoint retrieves a page and re-extracts its data from the stored HTML
    to show what the extraction process produces. Useful for testing and debugging.
    
    Args:
        page_id: ID of the scan page
        db: Database session
        
    Returns:
        Extracted data including metadata, headings, images, accessibility issues, etc.
    """
    try:
        # Get the page from database
        result = await db.execute(
            select(ScanPage).where(ScanPage.id == page_id)
        )
        page = result.scalar_one_or_none()
        
        if not page:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with ID {page_id} not found"
            )
        
        # Get the scan job to access stored HTML (if available)
        # Note: In the current implementation, HTML is not stored in the database
        # We would need to either:
        # 1. Store HTML in a separate field/table
        # 2. Re-scrape the page
        # 3. Store extracted data in a JSON field
        
        # For now, return page metadata and indicate that full extraction data needs storage
        page_info = {
            "page_id": page.id,
            "page_url": page.page_url,
            "page_title": page.page_title,
            "scan_job_id": page.scan_job_id,
            "http_status": page.http_status,
            "content_type": page.content_type,
            "content_length_bytes": page.content_length_bytes,
            "scores": {
                "overall": page.score_overall,
                "seo": page.score_seo,
                "accessibility": page.score_accessibility,
                "performance": page.score_performance,
                "design": page.score_design
            },
            "issues": {
                "critical_count": page.critical_issues_count,
                "warning_count": page.warning_issues_count
            },
            "note": "Full extracted data (metadata, headings, images, etc.) is processed during scan but not permanently stored. To see extraction results, use the POST /scan/scraping endpoint to re-extract from a URL."
        }
        
        return api_response(data=page_info)
        
    except HTTPException:
        raise
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to retrieve page data: {str(e)}",
            data={}
        )
