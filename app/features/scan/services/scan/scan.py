from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.platform.celery_app import celery_app

async def stop_scan_job(job_id: str, db: AsyncSession):
    job_query = select(ScanJob).where(ScanJob.id == job_id)
    result = await db.execute(job_query)
    job = result.scalar_one_or_none()
    if not job:
        return False
    if job.celery_task_id:
        celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGKILL")
    await db.execute(update(ScanJob).where(ScanJob.id == job_id).values(status=ScanJobStatus.failed, error_message="Scan stopped by user"))
    await db.execute(update(ScanPage).where(ScanPage.scan_job_id == job_id).values(is_selected_by_llm=False))
    await db.commit()
    return True