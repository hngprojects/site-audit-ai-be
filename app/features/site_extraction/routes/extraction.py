from fastapi import APIRouter, HTTPException, status

from app.features.site_extraction.schemas.metadata import (
    MetadataExtractionRequest,
    MetadataExtractionResult,
)
from app.features.site_extraction.services.page_loader_service import PageLoaderService
from app.features.site_extraction.services.extractor_service import ExtractorService
from app.platform.response import api_response

router = APIRouter(prefix="/extraction", tags=["extraction"])


@router.post(
    "/metadata",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Extract metadata from a URL",
    description="Analyze a web page and extract SEO metadata with validation",
)
async def extract_metadata(request: MetadataExtractionRequest):
    """
    Extract and validate metadata from a web page.
    
    This endpoint:
    1. Loads the provided URL using Selenium
    2. Extracts title, description, keywords, Open Graph tags, etc.
    3. Validates metadata against SEO best practices
    4. Returns structured results with actionable issues
    
    **Example Request:**
```json
    {
        "url": "https://example.com"
    }
```
    
    **Example Response:**
```json
    {
        "success": true,
        "message": "Metadata extracted successfully",
        "data": {
            "url": "https://example.com",
            "title": {
                "value": "Example Domain",
                "length": 14,
                "is_valid": false,
                "issues": [
                    {
                        "field": "title",
                        "severity": "warning",
                        "message": "Title is too short (14 chars). Recommended: 30-70 characters for optimal SEO."
                    }
                ]
            },
            "has_title": true,
            "overall_valid": false,
            "total_issues": 2
        }
    }
```
    """
    driver = None
    
    try:
        # Load the page
        driver = PageLoaderService.load_page(request.url)
        
        # Extract metadata
        metadata = ExtractorService.extract_metadata(driver)
        
        return api_response(
            data=metadata.model_dump(),
            message="Metadata extracted successfully",
            status_code=status.HTTP_200_OK,
        )
        
    except Exception as e:
        # Log error (you might want to add proper logging here)
        error_message = f"Failed to extract metadata: {str(e)}"
        
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=error_message,
            data={},
        )
        
    finally:
        # Always cleanup the driver
        if driver:
            try:
                driver.quit()
            except Exception:
                pass  # Ignore errors during cleanup