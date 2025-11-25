from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.scan.schemas.scan import ScrapingRequest, ScrapingResponse
from app.platform.response import api_response
from app.platform.db.session import get_db

router = APIRouter(prefix="/scan/scraping", tags=["scan-scraping"])


@router.post("", response_model=ScrapingResponse)
async def scrape_pages(
    data: ScrapingRequest,
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
        # TODO: Implement scraping service
        # - Scrape each page
        # - Store HTML, CSS, JS in ScanPage records
        # - Update ScanJob scraping_status
        
        return api_response(
            data={
                "scraped_pages": [],
                "count": 0,
                "job_id": data.job_id,
                "message": "Scraping service not yet implemented"
            }
        )
        
    except Exception as e:
        # TODO: If job_id provided, mark scraping_status = 'failed'
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Scraping failed: {str(e)}",
            data={}
        )
