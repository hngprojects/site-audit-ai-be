from fastapi import APIRouter, HTTPException, status
from app.features.page_discovery.schemas.discovery import DiscoveryRequest, DiscoveryResponse
from app.features.page_discovery.services.discovery_service import DiscoveryService
from app.platform.config import settings
from app.platform.response import api_response

router = APIRouter(prefix="/discovery", tags=["discovery"])

@router.post("")
async def enumerate_website(data: DiscoveryRequest):
    try:
        domain = data.url.host
        subdomains = DiscoveryService.enumerate_subdomains(domain)
        pages = DiscoveryService.discover_pages(str(data.url))
        all_urls = pages + [f"https://{sub}" for sub in subdomains if not sub.startswith("www.")]
        important_pages = DiscoveryService.filter_important_pages(
            all_urls,
            data.top_n
        )
        response_data = DiscoveryResponse(
            subdomains=subdomains,
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