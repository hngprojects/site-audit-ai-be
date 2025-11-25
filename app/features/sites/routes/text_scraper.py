from fastapi import APIRouter
from app.features.sites.schemas.text_scraper import TextScraperRequest, TextScraperResponse
from app.features.sites.services.text_scraper import SiteScraperService

router = APIRouter()

@router.post("/text-content", response_model=TextScraperResponse)
async def analyze_text_content(payload: TextScraperRequest):
    """
    Scrapes the URL and returns text analysis (Word count, readability, keyword density).
    """
    service = SiteScraperService()
    
    # Run the audit
    result = service.perform_text_scraping(str(payload.url), payload.keywords)
    
    return result