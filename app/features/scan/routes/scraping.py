from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import json
import time as time_module

from app.features.scan.schemas.scan import ScrapingRequest, ScrapingResponse
from app.features.scan.services.extraction.extractor_service import ExtractorService
from app.features.scan.services.scraping.scraping_service import ScrapingService
from app.features.scan.models.scan_page import ScanPage
from app.platform.response import api_response
from selenium.common.exceptions import TimeoutException

from app.platform.db.session import get_db
import hashlib

router = APIRouter(prefix="/scan/scraping", tags=["scan-scraping"])


async def scraping_progress_generator(url: str):
    """Generator that yields SSE events with real-time scraping progress"""
    driver = None
    
    try:
        # Send initial status
        yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing browser...'})}\n\n"
        await asyncio.sleep(0.1)
        
        # Build driver
        yield f"data: {json.dumps({'status': 'loading', 'message': 'Loading page...', 'elapsed': 0})}\n\n"
        
        # Start loading in a thread since Selenium is blocking
        import threading
        from queue import Queue
        
        result_queue = Queue()
        error_queue = Queue()
        start_time = time_module.time()
        
        def load_page_thread():
            try:
                driver_local = ScrapingService.load_page(str(url), timeout=30)
                result_queue.put(driver_local)
            except Exception as e:
                error_queue.put(e)
        
        thread = threading.Thread(target=load_page_thread)
        thread.start()
        
        # Send progress updates while loading
        while thread.is_alive():
            elapsed = time_module.time() - start_time
            
            # Progressive messages based on elapsed time
            if elapsed < 3.0:
                # Still reasonable, just show progress
                message = "Loading page..."
            elif elapsed < 5.0:
                # Starting to take longer than expected
                message = "Page is taking longer than expected..."
            elif elapsed < 10.0:
                # Definitely slow
                message = "Warning: Page is loading slowly..."
            else:
                # Very slow
                message = "Critical: Page is taking very long to load..."
            
            yield f"data: {json.dumps({'status': 'loading', 'message': message, 'elapsed': round(elapsed, 2)})}\n\n"
            await asyncio.sleep(0.5)
        
        thread.join()
        
        # Check for errors
        if not error_queue.empty():
            error = error_queue.get()
            if isinstance(error, TimeoutException):
                yield f"data: {json.dumps({'status': 'error', 'message': 'Page took too long to load (timeout)', 'error': str(error)})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'error', 'message': 'Failed to load page', 'error': str(error)})}\n\n"
            return
        
        driver = result_queue.get()
        load_time = time_module.time() - start_time
        
        # Calculate performance now that we know the final load time
        loading_status = getattr(driver, "performance_metrics", {}).get("loading_status", None)
        performance_score = ScrapingService.calculate_performance_score(load_time)
        performance_comment = ScrapingService.get_performance_comment(performance_score, loading_status)
        
        # Page loaded successfully - NOW we assess performance
        yield f"data: {json.dumps({'status': 'loaded', 'message': performance_comment, 'load_time': round(load_time, 2), 'score': performance_score})}\n\n"
        await asyncio.sleep(0.1)
        
        # Extract data
        yield f"data: {json.dumps({'status': 'extracting', 'message': 'Extracting page data...'})}\n\n"
        
        headings = ExtractorService.extract_headings(driver)
        images = ExtractorService.extract_images(driver)
        issues = ExtractorService.extract_accessibility(driver, headings=headings, images=images)
        text_content = ExtractorService.extract_text_content(driver)
        metadata = ExtractorService.extract_metadata(driver)
        
        # Performance Metrics
        loading_status = getattr(driver, "performance_metrics", {}).get("loading_status", None)
        performance_score = ScrapingService.calculate_performance_score(load_time)
        performance_comment = ScrapingService.get_performance_comment(performance_score, loading_status)
        
        response_data = {
            "heading_data": headings,
            "images_data": images,
            "issues_data": issues,
            "text_content_data": text_content,
            "metadata_data": metadata,
            "performance_data": {
                "load_time": load_time,
                "score": performance_score,
                "comment": performance_comment
            }
        }
        
        # Send completion with data
        yield f"data: {json.dumps({'status': 'complete', 'message': 'Scraping completed!', 'data': response_data})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


@router.get("/stream")
async def scrape_page_stream(url: str):
    """
    Stream real-time scraping progress using Server-Sent Events (SSE).
    
    Returns a stream of JSON events with status updates:
    - starting: Browser initialization
    - loading: Page is loading (with elapsed time)
    - slow/very_slow: Page is taking longer than expected
    - loaded: Page loaded successfully
    - extracting: Extracting data from page
    - complete: Scraping finished (includes full data)
    - error: An error occurred
    
    Example usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/scan/scraping/stream?url=https://example.com');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.status, data.message);
    };
    ```
    """
    return StreamingResponse(
        scraping_progress_generator(url),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


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
        driver = None

        try:
            page_url = str(url)
            driver = ScrapingService.load_page(page_url)

            # Use the unified extract_from_html method
            # First get the HTML
            html = driver.page_source
            
            # Extract all data using the standardized method
            extracted_data = ExtractorService.extract_from_html(html, page_url)
            
            return api_response(
                message=f"Successfully extracted data from {page_url}",
                data=extracted_data
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
    # data: ScrapingRequest,
    url,
    db: AsyncSession = Depends(get_db)
):
    """
    This endpoint:
    - Takes selected pages
    - Uses Selenium to scrape full page content
    - Creates ScanPage records for each page
    
    Called by: Scraping worker after selection completes
    
    Args:
        data: ScrapingRequest with pages to scrape
        db: Database session
        
    Returns:
        ScrapingResponse with scraped page data
    """
    try:
        driver = None

        try:
            page_url = str(url)
            driver = ScrapingService.load_page(page_url, timeout=30)  # Increased timeout to 30s

            # Extractor Engines
            headings = ExtractorService.extract_headings(driver)
            images = ExtractorService.extract_images(driver)
            issues = ExtractorService.extract_accessibility(driver, headings=headings, images=images)
            text_content = ExtractorService.extract_text_content(driver)
            metadata = ExtractorService.extract_metadata(driver)

            # Performance Metrics
            load_time = getattr(driver, "performance_metrics", {}).get("load_time", 0.0)
            loading_status = getattr(driver, "performance_metrics", {}).get("loading_status", None)
            performance_score = ScrapingService.calculate_performance_score(load_time)
            performance_comment = ScrapingService.get_performance_comment(performance_score, loading_status)

            response_data = {
                "heading_data" : headings,
                "images_data" : images,
                "issues_data" : issues,
                "text_content_data" : text_content,
                "metadata_data" : metadata,
                "performance_data": {
                    "load_time": load_time,
                    "score": performance_score,
                    "comment": performance_comment
                }
            }
            
            return api_response(data=response_data)
        except TimeoutException as e:
            return api_response(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                message=f"Page took too long to load (timeout after 30s). The page may be slow or unresponsive.",
                data={"url": str(url)}
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return api_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=str(e),
                data={}
            )
        finally:
            if driver:
                driver.quit()
            
    except Exception as e:
        # TODO: If job_id provided, mark scraping_status = 'failed'
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Scraping failed: {str(e)}",
            data={}
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
