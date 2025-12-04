import logging     
import asyncio     
from kombu import Connection
from app.platform.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.platform.celery_app import celery_app
from sqlalchemy import delete
from typing import Dict, Any
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

async def stop_scan_job(job_id: str, db: AsyncSession):
    job_query = select(ScanJob).where(ScanJob.id == job_id)
    result = await db.execute(job_query)
    job = result.scalar_one_or_none()
    
    if not job:
        logger.warning(f"Stop requested for non-existent job {job_id}")
        return False

    if job.status in {ScanJobStatus.completed, ScanJobStatus.failed, ScanJobStatus.cancelled}:
        logger.info(f"Job {job_id} already in terminal state: {job.status}")
        return True

    await db.execute(
        update(ScanJob)
        .where(ScanJob.id == job_id)
        .values(
            status=ScanJobStatus.cancelled,
            error_message="Scan stopped by user"
        )
    )
    await db.commit()
    logger.info(f"Marked job {job_id} as cancelled in DB")
    
    await asyncio.sleep(0.5)
    
    if job.celery_task_id:
        try:
            celery_app.control.revoke(
                job.celery_task_id,
                terminate=True,
                signal='SIGTERM'
            )
            logger.info(f"Revoked Celery task {job.celery_task_id} for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error revoking Celery task {job.celery_task_id}: {e}")
    
    return True

async def delete_scan_job(
    db: AsyncSession,
    job_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Task 3: Delete an individual scan record.
    
    Uses the efficient SQL DELETE approach to ensure the scan belongs to the user
    and is deleted in a single query.
    """
    try:
        # Efficiently delete the scan using a single SQL DELETE statement
        stmt = delete(ScanJob).where(
            ScanJob.id == job_id,
            ScanJob.user_id == user_id
        )
        
        result = await db.execute(stmt)
        await db.commit()
        
        # Check if any row was affected (i.e., if the scan existed and belonged to the user)
        if result.rowcount == 0:
            logger.warning(f"Delete requested for scan {job_id} not found or doesn't belong to user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found or not owned by user"
            )
        
        logger.info(f"Successfully deleted scan {job_id} for user {user_id}")
        
        return {
            "message": "Scan deleted successfully.",
            "job_id": job_id
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 404 from rowcount check)
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error deleting scan {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting scan: {str(e)}"
        )