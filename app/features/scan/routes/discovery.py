from fastapi import APIRouter, status, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

from app.features.scan.schemas.scan import DiscoveryRequest, DiscoveryResponse
from app.features.scan.services.discovery.page_discovery import PageDiscoveryService
from app.features.scan.services.analysis.page_selector import PageSelectorService
from app.features.auth.routes.auth import get_current_user, decode_access_token
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
    title: str
    url: str
    priority: str  # "High Priority", "Medium Priority", "Low Priority"
    description: str


class DiscoverUrlsResponse(BaseModel):
    """Response with top 10 important URLs"""
    base_url: str
    discovered_count: int  # Total discovered (max 10)
    important_urls: List[DiscoveredUrl]  # Top 10 ranked by LLM
    message: str


@router.post("/discover-urls", response_model=DiscoverUrlsResponse)
async def discover_important_urls(
    data: DiscoverUrlsRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
):
    """
    Discover and return top 10 most important URLs from a website.
    
    **Process:**
    1. Validates the input URL
    2. Discovers up to 10 pages using lightweight Selenium crawler
    3. Ensures all URLs share the same base domain
    4. Uses LLM (OpenRouter) to rank pages by importance
    5. Returns top 10 most important URLs
    
    **Authentication:** Optional - works for both authenticated and anonymous users
    
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
                {
                    "title": "Home",
                    "url": "https://example.com",
                    "priority": "High Priority",
                    "description": "Your main landing page, and the first impression customers get of your brand"
                },
                {
                    "title": "About",
                    "url": "https://example.com/about",
                    "priority": "Medium Priority",
                    "description": "This page tells visitors about your company, mission, and team"
                }
            ],
            "message": "Successfully discovered 10 important URLs"
        }
    }
    ```
    """
    try:
        url_str = str(data.url)
        
        is_valid, validated_url, error_message = validate_url(url_str)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid URL: {error_message}"
            )
        
        # Get user if authenticated (optional)
        user_id = None
        if credentials:
            try:
                payload = decode_access_token(credentials.credentials)
                user_id = payload.get("sub")
            except Exception:
                pass  # Continue without authentication
        
        logger.info(f"User {user_id or 'anonymous'} initiated URL discovery for {validated_url}")
        
        # Step 1: Discover up to 10 pages
        discovery_service = PageDiscoveryService()
        discovered_pages = discovery_service.discover_pages(
            url=validated_url,
            max_pages=10
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
        
        # Step 2: Use LLM to rank and generate metadata for top 10 important pages
        annotated_pages = PageDiscoveryService.fallback_selection(
            pages=discovered_pages,
            max_pages=10
        )
        
        # Convert to DiscoveredUrl objects
        important_urls = [
            DiscoveredUrl(**page) for page in annotated_pages
        ]
        
        logger.info(f"Selected {len(important_urls)} important URLs for {validated_url}")
        return api_response(
            data={
                "base_url": validated_url,
                "discovered_count": len(discovered_pages),
                "important_urls": [url.dict() for url in important_urls],
                "message": f"Successfully discovered {len(important_urls)} important URLs"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL discovery failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover URLs: {str(e)}"
        )
