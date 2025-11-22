from fastapi import APIRouter, HTTPException
from app.features.scraping.schemas.scraping_schema import ScrapeRequest, ScrapeResponse
from app.features.scraping.services.selenium_service import SeleniumService

router = APIRouter(prefix="/scraping", tags=["scraping"])
selenium_service = SeleniumService()

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    try:
        result = selenium_service.scrape_url(str(request.url))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape URL: {str(e)}")
