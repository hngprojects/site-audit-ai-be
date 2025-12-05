from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.scan.schemas.scan import DiscoveryRequest, DiscoveryResponse
from app.features.scan.services.discovery.page_discovery import PageDiscoveryService
from app.platform.response import api_response
from app.platform.db.session import get_db

router = APIRouter(prefix="/scan/discovery", tags=["scan-discovery"])


@router.post("", response_model=DiscoveryResponse)
async def discover_pages(
    data: DiscoveryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Phase 1: Discover important pages from a website using LLM.
    
    This endpoint:
    - Uses LLM to analyze the website URL and identify important pages
    - Returns list of discovered URLs (up to 10 important pages)
    
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
