from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from app.features.scan.schemas.scan import SelectionRequest, SelectionResponse
from app.features.scan.services.analysis.page_selector import PageSelectorService
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.platform.response import api_response
from app.platform.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan/selection", tags=["scan-selection"])


@router.post("", response_model=SelectionResponse)
async def select_important_pages(
    data: SelectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Select important pages from discovered pages using LLM.
    
    This endpoint:
    - Calls PageSelectorService to use OpenRouter LLM for intelligent page selection
    - Updates ScanPage records with is_selected_by_llm flag
    - Updates ScanJob with pages_selected count and status
    
    Args:
        data: SelectionRequest with pages list, top_n, job_id, etc.
        db: Database session
        
    Returns:
        SelectionResponse with selected pages
    """
    try:
        logger.info(f"Starting page selection for job_id={data.job_id}, {len(data.pages)} pages, top_n={data.top_n}")
        
        # Call LLM-based selection service
        important_pages = PageSelectorService.filter_important_pages(
            data.pages,
            data.top_n,
            referer=data.referer or "https://sitemate-ai.com",
            site_title=data.site_title or "SiteMate AI"
        )
        
        logger.info(f"LLM selected {len(important_pages)} pages from {len(data.pages)} discovered pages")
        
        # Update database if job_id provided
        if data.job_id:
            # Update ScanPage records to mark selected pages
            for page_url in important_pages:
                result = await db.execute(
                    update(ScanPage)
                    .where(
                        ScanPage.scan_job_id == data.job_id,
                        ScanPage.page_url == page_url
                    )
                    .values(is_selected_by_llm=True)
                )
            
            # Update ScanJob with selection results
            await db.execute(
                update(ScanJob)
                .where(ScanJob.id == data.job_id)
                .values(
                    pages_selected=len(important_pages),
                    status=ScanJobStatus.selecting
                )
            )
            
            await db.commit()
            logger.info(f"Updated ScanJob {data.job_id} with {len(important_pages)} selected pages")
        
        return api_response(
            data={
                "important_pages": important_pages,
                "count": len(important_pages),
                "job_id": data.job_id
            },
            message=f"Successfully selected {len(important_pages)} important pages"
        )
        
    except Exception as e:
        logger.error(f"Selection failed: {str(e)}", exc_info=True)
        
        # Mark job as failed if job_id provided
        if data.job_id:
            try:
                await db.execute(
                    update(ScanJob)
                    .where(ScanJob.id == data.job_id)
                    .values(
                        status=ScanJobStatus.failed,
                        error_message=f"Page selection failed: {str(e)}"
                    )
                )
                await db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update job status: {str(db_err)}")
        
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Selection failed: {str(e)}",
            data={}
        )
