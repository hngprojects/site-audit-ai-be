from fastapi import APIRouter, status, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, HttpUrl

from app.features.scan.schemas.scan import DiscoveryRequest, DiscoveryResponse
from app.features.scan.services.discovery.page_discovery import PageDiscoveryService
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.platform.response import api_response
from app.platform.db.session import get_db

router = APIRouter(prefix="/scan/discovery", tags=["scan-discovery"])

class AddPageRequest(BaseModel):
    job_id: str
    url: HttpUrl

@router.post("", response_model=DiscoveryResponse)
async def discover_pages(
    data: DiscoveryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Phase 1: Discover pages using LLM suggestions.
    
    This endpoint:
    - Uses LLM to suggest likely pages based on the URL
    - Saves discovered pages to database if job_id is provided
    
    Args:
        data: DiscoveryRequest with url and optional job_id
        db: Database session
        
    Returns:
        DiscoveryResponse with discovered pages
    """
    try:
        url_str = str(data.url)
        
        # Run suggestion (LLM) - ONLY LLM as requested
        suggested_pages = PageDiscoveryService.suggest_pages(url_str)
        
        all_pages = list(set(suggested_pages))
        
        if data.job_id:
            # Save to DB
            # First check which pages already exist for this job
            existing_result = await db.execute(
                select(ScanPage.page_url).where(ScanPage.scan_job_id == data.job_id)
            )
            existing_urls = set(existing_result.scalars().all())
            
            new_pages_count = 0
            for page_url in all_pages:
                if page_url not in existing_urls:
                    page_normalized = page_url.rstrip('/')
                    scan_page = ScanPage(
                        scan_job_id=data.job_id,
                        page_url=page_url,
                        page_url_normalized=page_normalized,
                        is_selected_by_llm=False,
                        is_manually_selected=False,
                        is_manually_deselected=False
                    )
                    db.add(scan_page)
                    new_pages_count += 1
            
            if new_pages_count > 0:
                await db.commit()
                
                # Update Job status
                await db.execute(
                    update(ScanJob)
                    .where(ScanJob.id == data.job_id)
                    .values(
                        pages_discovered=len(existing_urls) + new_pages_count,
                        status=ScanJobStatus.selecting # Ready for selection
                    )
                )
                await db.commit()
        
        return api_response(
            data={
                "pages": all_pages,
                "count": len(all_pages),
                "job_id": data.job_id
            }
        )
        
    except Exception as e:
        if data.job_id:
            try:
                await db.execute(
                    update(ScanJob)
                    .where(ScanJob.id == data.job_id)
                    .values(
                        status=ScanJobStatus.failed,
                        error_message=f"Discovery failed: {str(e)}"
                    )
                )
                await db.commit()
            except:
                pass
                
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Discovery failed: {str(e)}",
            data={}
        )

@router.post("/add", response_model=dict)
async def add_discovered_page(
    data: AddPageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually add a URL to the discovered pages list for a job.
    """
    try:
        url_str = str(data.url)
        
        # Check if job exists
        job = await db.scalar(select(ScanJob).where(ScanJob.id == data.job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Scan job not found")
            
        # Check if page already exists
        existing = await db.scalar(
            select(ScanPage).where(
                ScanPage.scan_job_id == data.job_id,
                ScanPage.page_url == url_str
            )
        )
        
        if existing:
            return api_response(
                message="Page already exists in discovery list",
                data={"page_id": existing.id, "url": existing.page_url}
            )
            
        # Add new page
        page_normalized = url_str.rstrip('/')
        new_page = ScanPage(
            scan_job_id=data.job_id,
            page_url=url_str,
            page_url_normalized=page_normalized,
            is_selected_by_llm=False,
            is_manually_selected=True, # Mark as manually added/selected
            is_manually_deselected=False
        )
        db.add(new_page)
        
        # Update job count
        job.pages_discovered = (job.pages_discovered or 0) + 1
        
        await db.commit()
        await db.refresh(new_page)
        
        return api_response(
            message="Page added successfully",
            data={"page_id": new_page.id, "url": new_page.page_url}
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        await db.rollback()
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to add page: {str(e)}",
            data={}
        )


@router.get("/{job_id}", response_model=dict)
async def get_discovered_pages(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all discovered pages for a specific scan job.
    """
    try:
        # Check if job exists
        job = await db.scalar(select(ScanJob).where(ScanJob.id == job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Scan job not found")

        # Fetch pages
        result = await db.execute(
            select(ScanPage).where(ScanPage.scan_job_id == job_id)
        )
        pages = result.scalars().all()

        return api_response(
            data={
                "job_id": job_id,
                "pages": [
                    {
                        "id": page.id,
                        "url": page.page_url,
                        "is_manually_selected": page.is_manually_selected
                    } 
                    for page in pages
                ],
                "count": len(pages)
            },
            message="Discovered pages retrieved successfully"
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to retrieve pages: {str(e)}",
            data={}
        )
