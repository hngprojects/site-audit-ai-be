from fastapi import APIRouter,  status
from app.features.page_extractor.schemas.extractor_schema import ExtractorRequest
from app.features.page_extractor.services.extractor_service import ExtractorService
from app.platform.response import api_response


router = APIRouter(prefix="/extractor", tags=["extractor"])

@router.post("")
async def analyze_page(request:ExtractorRequest):
    driver = None
    try:
        page_url = str(request.url)
        driver = ExtractorService.load_page(page_url)

        # Extractor Engines
        headings = ExtractorService.extract_headings(driver)
        images = ExtractorService.extract_images(driver)
        issues = ExtractorService.extract_accessibility(driver, headings=headings, images=images)

        response_data = {
            "heading_data" : headings,
            "images_data" : images,
            "issues_data" : issues
        }
        return api_response(data=response_data)
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=str(e),
            data={}
        )
    finally:
        if driver:
            driver.quit()