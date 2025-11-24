from fastapi import APIRouter, HTTPException, status
from app.features.page_discovery.schemas.discovery import DiscoveryRequest, DiscoveryResponse
from app.features.page_discovery.services.discovery_service import DiscoveryService
from app.platform.config import settings
from app.platform.response import api_response

router = APIRouter(prefix="/discovery", tags=["discovery"])

@router.post("")
async def enumerate_website(data: DiscoveryRequest):
    try:
        pages = DiscoveryService.discover_pages(str(data.url))
        important_pages = DiscoveryService.filter_important_pages(
            pages,
            data.top_n
        )
        response_data = DiscoveryResponse(
            pages=pages,
            important_pages=important_pages
        )
        return api_response(data=response_data)
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=str(e),
            data={}
        )