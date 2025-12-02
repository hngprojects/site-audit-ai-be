import logging     
import asyncio     
from kombu import Connection
from app.platform.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.platform.celery_app import celery_app

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