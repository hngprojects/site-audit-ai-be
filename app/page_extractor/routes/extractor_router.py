from fastapi import APIRouter, HTTPException, status
from app.features.page_extractor.schemas.extractor_schema import ExtractorRequest, ExtractorResponse
from app.features.page_discovery.services.discovery_service import DiscoveryService
from app.platform.config import settings
from app.platform.response import api_response


router = APIRouter(prefix="/discovery", tags=["discovery"])

@router.post("")
async def get_website_detail(data):

    try:
        response_data = DiscoveryService.sample(data)
        # response_data = DiscoveryResponse(
        #     subdomains=subdomains,
        #     pages=pages,
        #     important_pages=important_pages
        # )
        return api_response(data=response_data)
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=str(e),
            data={}
        )
