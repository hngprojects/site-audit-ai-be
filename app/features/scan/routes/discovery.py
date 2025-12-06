from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl
from typing import List

from app.features.scan.schemas.scan import DiscoveryRequest, DiscoveryResponse
from app.features.scan.services.discovery.page_discovery import PageDiscoveryService
from app.features.scan.services.analysis.page_selector import PageSelectorService
from app.features.auth.routes.auth import get_current_user
from app.features.auth.models.user import User
from app.platform.response import api_response
from app.platform.db.session import get_db
from app.platform.utils.url_validator import validate_url
from app.platform.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/scan/discovery", tags=["scan-discovery"])


class DiscoverUrlsRequest(BaseModel):
    """Request schema for URL discovery"""
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com"
            }
        }


class DiscoveredUrl(BaseModel):
    """Individual discovered URL with metadata"""
    url: str
    rank: int  # 1-10, with 1 being most important


class DiscoverUrlsResponse(BaseModel):
    """Response with top 10 important URLs"""
    base_url: str
    discovered_count: int  # Total discovered (max 15)
    important_urls: List[DiscoveredUrl]  # Top 10 ranked by LLM
    message: str


@router.post("", response_model=DiscoveryResponse)
async def discover_pages(
    data: DiscoveryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Phase 1: Discover all pages from a website using Selenium.
    
    This endpoint:
    - Crawls the website using headless Chrome
    - Returns list of discovered URLs
    
    Later-> Called by: Discovery worker after scan is queued
    
    Args:
        data: DiscoveryRequest with url and optional job_id
        db: Database session
        
    Returns:
        DiscoveryResponse with discovered pages
    """
    try:
        # Run discovery
        pages = PageDiscoveryService.discover_pages(str(data.url))
        
        # TODO: If job_id provided, update ScanJob record
        # - Set status = 'discovered'
        # - Set discovered_pages_count = len(pages)
        # - Queue next phase (selection)
        
        return api_response(
            data={
                "pages": pages,
                "count": len(pages),
                "job_id": data.job_id
            }
        )
        
    except Exception as e:
        # TODO: If job_id provided, mark discovery_status = 'failed'
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Discovery failed: {str(e)}",
            data={}
        )


@router.post("/discover-urls", response_model=DiscoverUrlsResponse)
async def discover_important_urls(
    data: DiscoverUrlsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Discover and return top 10 most important URLs from a website.
    
    **Process:**
    1. Validates the input URL
    2. Discovers up to 15 pages using lightweight Selenium crawler
    3. Ensures all URLs share the same base domain
    4. Uses LLM (OpenRouter) to rank pages by importance
    5. Returns top 10 most important URLs
    
    **Authentication:** Required - only logged-in users can access
    
    **Returns:**
    - List of top 10 URLs ranked by importance
    - Empty array if no URLs found
    
    **Example Response:**
    ```json
    {
        "status_code": 200,
        "status": "success",
        "message": "Successfully discovered 10 important URLs",
        "data": {
            "base_url": "https://example.com",
            "discovered_count": 15,
            "important_urls": [
                {"url": "https://example.com", "rank": 1},
                {"url": "https://example.com/about", "rank": 2}
            ],
            "message": "Successfully discovered 10 important URLs"
        }
    }
    ```
    """
    try:
        url_str = str(data.url)
        
        # Validate URL
        is_valid, validated_url, error_message = validate_url(url_str)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid URL: {error_message}"
            )
        
        logger.info(f"User {current_user.id} initiated URL discovery for {validated_url}")
        
        # Step 1: Discover up to 15 pages
        discovery_service = PageDiscoveryService()
        discovered_pages = discovery_service.discover_pages(
            url=validated_url,
            max_pages=15
        )
        
        if not discovered_pages:
            return api_response(
                message="No URLs found for the given website",
                data={
                    "base_url": validated_url,
                    "discovered_count": 0,
                    "important_urls": [],
                    "message": "No URLs found for the given website"
                }
            )
        
        logger.info(f"Discovered {len(discovered_pages)} pages from {validated_url}")
        
        # Step 2: Use LLM to select top 10 important pages
        selector_service = PageSelectorService()
        selected_urls = selector_service.filter_important_pages(
            pages=discovered_pages,
            top_n=10,
            referer=validated_url,
            site_title=f"URL Discovery for {validated_url}"
        )
        
        # Step 3: Format response with ranking
        important_urls = [
            DiscoveredUrl(url=url, rank=idx + 1) 
            for idx, url in enumerate(selected_urls)
        ]
        
        logger.info(f"Selected {len(important_urls)} important URLs for {validated_url}")
        
        return api_response(
            message=f"Successfully discovered {len(important_urls)} important URLs",
            data={
                "base_url": validated_url,
                "discovered_count": len(discovered_pages),
                "important_urls": important_urls,
                "message": f"Successfully discovered {len(important_urls)} important URLs"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL discovery failed for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover URLs: {str(e)}"
        )
