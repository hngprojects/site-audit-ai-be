from fastapi import APIRouter, HTTPException, status
from app.features.scraping.schemas.scraping_schema import ScrapeRequest, ScrapeResponse
from app.features.scraping.services.selenium_service import SeleniumService

router = APIRouter(prefix="/scraping", tags=["Scraping"])

@router.post("/scrape", response_model=ScrapeResponse, status_code=status.HTTP_200_OK)
async def scrape_url(request: ScrapeRequest):
    service = SeleniumService()
    try:
        result = service.scrape_url(str(request.url))
        return ScrapeResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape URL: {str(e)}"
        )
