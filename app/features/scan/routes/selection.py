from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.scan.schemas.scan import SelectionRequest, SelectionResponse
from app.features.scan.services.analysis.page_selector import PageSelectorService
from app.platform.response import api_response
from app.platform.db.session import get_db

router = APIRouter(prefix="/scan/selection", tags=["scan-selection"])


@router.post("", response_model=SelectionResponse)
async def select_important_pages(
    data: SelectionRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        important_pages = PageSelectorService.filter_important_pages(
            data.pages,
            data.top_n,
            referer=data.referer or "",
            site_title=data.site_title or ""
        )
        
        # TODO: update ScanJob record
        # - Queue next phase (scraping)
        
        return api_response(
            data={
                "important_pages": important_pages,
                "count": len(important_pages),
                "job_id": data.job_id
            }
        )
        
    except Exception as e:
        # TODO: mark selection_status = 'failed'
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Selection failed: {str(e)}",
            data={}
        )
