from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.scan.schemas.scan import (
    GetPagesRequest,
    GetPagesResponse,
    TogglePageSelectionRequest,
    TogglePageSelectionResponse,
    PageInfo
)
from app.features.scan.models.scan_page import ScanPage
from app.platform.response import api_response
from app.platform.db.session import get_db

router = APIRouter(prefix="/scan/pages", tags=["scan-pages"])


@router.get("/{job_id}")
async def get_job_pages(
    job_id: str,
    filter: str = "all",
    db: AsyncSession = Depends(get_db)
):
    """
    Get all discovered pages for a scan job.
    
    Allows users to see:
    - All discovered pages
    - Which ones the LLM selected
    - Which ones they manually selected/deselected
    
    Args:
        job_id: The scan job ID
        filter: 'all', 'selected', 'not_selected', 'llm_selected'
        db: Database session
        
    Returns:
        GetPagesResponse with all pages and selection status
    """
    try:
        # Query all pages for this job
        query = select(ScanPage).where(ScanPage.scan_job_id == job_id)
        result = await db.execute(query)
        pages = result.scalars().all()
        
        if not pages:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No pages found for this job. Run discovery first.",
                data={}
            )
        
        # Convert to PageInfo with computed is_selected
        page_infos = [
            PageInfo(
                id=page.id,
                page_url=page.page_url,
                is_selected_by_llm=page.is_selected_by_llm,
                is_manually_selected=page.is_manually_selected,
                is_manually_deselected=page.is_manually_deselected,
                is_selected=page.is_selected  # Uses @property
            )
            for page in pages
        ]
        
        # Apply filter
        if filter == "selected":
            page_infos = [p for p in page_infos if p.is_selected]
        elif filter == "not_selected":
            page_infos = [p for p in page_infos if not p.is_selected]
        elif filter == "llm_selected":
            page_infos = [p for p in page_infos if p.is_selected_by_llm]
        
        # Calculate stats
        total_selected = sum(1 for p in page_infos if p.is_selected)
        total_llm_selected = sum(1 for p in page_infos if p.is_selected_by_llm)
        total_manually_added = sum(1 for p in page_infos if p.is_manually_selected)
        
        return api_response(
            data={
                "job_id": job_id,
                "pages": [p.dict() for p in page_infos],
                "total_discovered": len(pages),
                "total_selected": total_selected,
                "total_llm_selected": total_llm_selected,
                "total_manually_added": total_manually_added
            }
        )
        
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching pages: {str(e)}",
            data={}
        )


@router.post("/toggle")
async def toggle_page_selection(
    data: TogglePageSelectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually select or deselect a page for scanning.
    
    This allows users to:
    - Add pages the LLM didn't select
    - Remove pages the LLM selected
    
    Args:
        data: TogglePageSelectionRequest with page_id and action
        db: Database session
        
    Returns:
        TogglePageSelectionResponse with updated selection status
    """
    try:
        # Get the page
        query = select(ScanPage).where(ScanPage.id == data.page_id)
        result = await db.execute(query)
        page = result.scalar_one_or_none()
        
        if not page:
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Page not found",
                data={}
            )
        
        # Apply action
        if data.action == "select":
            page.is_manually_selected = True
            page.is_manually_deselected = False
            message = f"Page manually selected for scanning"
        elif data.action == "deselect":
            page.is_manually_selected = False
            page.is_manually_deselected = True
            message = f"Page manually excluded from scanning"
        else:
            return api_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid action. Use 'select' or 'deselect'",
                data={}
            )
        
        await db.commit()
        await db.refresh(page)
        
        return api_response(
            data={
                "page_id": page.id,
                "page_url": page.page_url,
                "is_selected": page.is_selected,
                "message": message
            }
        )
        
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error toggling page selection: {str(e)}",
            data={}
        )
