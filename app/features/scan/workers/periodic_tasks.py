"""
Celery periodic tasks for automated site scanning.

This module contains tasks that run on a schedule via Celery Beat.
"""
import logging
from datetime import datetime, timedelta
from celery import shared_task

from app.platform.celery_app import celery_app

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="app.features.scan.workers.periodic_tasks.check_and_trigger_periodic_scans")
def check_and_trigger_periodic_scans(self):
    """
    Periodic task that checks for sites due for scanning and triggers scans.
    
    Runs every hour via Celery Beat.
    Queries sites where:
    - scan_frequency_enabled = True
    - next_scheduled_scan <= now()
    
    For each site due for scanning:
    1. Triggers async scan via run_scan_pipeline.delay()
    2. Updates next_scheduled_scan based on frequency
    3. Sends email report after scan completes
    """
    from app.features.scan.workers.tasks import get_sync_db
    from app.features.sites.models.site import Site, ScanFrequency
    from app.features.scan.workers.tasks import run_scan_pipeline
    from sqlalchemy import select
    from app.features.auth.models.user import User
    
    logger.info("Checking for sites due for periodic scanning...")
    
    db = get_sync_db()
    
    try:
        # Query sites that need scanning
        now = datetime.utcnow()
        query = select(Site).where(
            Site.scan_frequency_enabled == True,
            Site.next_scheduled_scan <= now,
            Site.scan_frequency != ScanFrequency.disabled
        )
        
        result = db.execute(query)
        sites_to_scan = result.scalars().all()
        
        logger.info(f"Found {len(sites_to_scan)} sites due for periodic scanning")
        
        for site in sites_to_scan:
            try:
                logger.info(f"Triggering periodic scan for site {site.id} ({site.root_url})")
                
                # Create ScanJob first (similar to start_scan_async route)
                from app.features.scan.models.scan_job import ScanJob
                import hashlib
                
                device_id = None if site.user_id else f"periodic-{hashlib.sha256(site.root_url.encode()).hexdigest()[:16]}"
                
                scan_job = ScanJob(
                    user_id=site.user_id,
                    device_id=device_id,
                    site_id=site.id,
                    status="queued",
                    queued_at=now
                )
                db.add(scan_job)
                db.flush()  # Get the job ID
                
                # Update next_scheduled_scan based on frequency
                if site.scan_frequency == ScanFrequency.weekly:
                    site.next_scheduled_scan = now + timedelta(days=7)
                elif site.scan_frequency == ScanFrequency.monthly:
                    site.next_scheduled_scan = now + timedelta(days=30)
                elif site.scan_frequency == ScanFrequency.quarterly:
                    site.next_scheduled_scan = now + timedelta(days=90)
                
                site.last_periodic_scan_at = now
                
                # IMPORTANT: Commit BEFORE triggering Celery task
                # This ensures the scan_job exists in DB when worker tries to access it
                db.commit()
                
                # Trigger async scan pipeline AFTER commit
                # Get user email and name for notification
                user_email = None
                user_name = None
                if site.user_id:
                    # We need to fetch the user to get their email
                    # Since we can't easily do a join here with the current setup, 
                    # let's fetch the user separately
                    user = db.query(User).filter(User.id == site.user_id).first()
                    if user:
                        user_email = user.email
                        user_name = user.first_name
                
                task_result = run_scan_pipeline.delay(
                    job_id=str(scan_job.id),
                    url=site.root_url,
                    top_n=5,
                    max_pages=1,
                    notification_email=user_email,
                    user_name=user_name
                )
                
                logger.info(f"Scheduled next scan for {site.root_url} at {site.next_scheduled_scan}")
                
            except Exception as e:
                logger.error(f"Error triggering periodic scan for site {site.id}: {e}")
                db.rollback()
                continue
        
        return {
            "status": "success",
            "sites_scanned": len(sites_to_scan),
            "timestamp": now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in check_and_trigger_periodic_scans: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        db.close()


@shared_task(bind=True, name="app.features.scan.workers.periodic_tasks.send_scan_completion_email")
def send_scan_completion_email(self, job_id: str, user_email: str, user_name: str, site_name: str):
    """
    Send email notification when a periodic scan completes.
    
    Args:
        job_id: The completed scan job ID
        user_email: User's email address
        user_name: User's first name
        site_name: Name of the scanned site
    """
    from app.features.scan.workers.tasks import get_sync_db
    from app.features.scan.models.scan_job import ScanJob
    from app.features.sites.services.scan_report_email import send_scan_report_email
    from sqlalchemy import select
    
    logger.info(f"Sending scan completion email for job {job_id} to {user_email}")
    
    db = get_sync_db()
    
    try:
        # Get scan job results
        query = select(ScanJob).where(ScanJob.id == job_id)
        result = db.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            logger.error(f"Scan job {job_id} not found")
            return {"status": "error", "message": "Job not found"}
        
        # Prepare scan results for email
        scan_results = {
            "job_id": job.id,
            "score_overall": job.score_overall or 0,
            "score_seo": job.score_seo or 0,
            "score_accessibility": job.score_accessibility or 0,
            "score_performance": job.score_performance or 0,
            "score_design": job.score_design or 0,
            "critical_issues_count": job.critical_issues_count or 0,
            "warning_issues_count": job.warning_issues_count or 0,
            "total_issues": job.total_issues or 0,
        }
        
        # Get site name from job's site relationship or use passed site_name as fallback
        actual_site_name = site_name
        if job.site and job.site.display_name:
            actual_site_name = job.site.display_name
        elif job.site and job.site.root_url:
            actual_site_name = job.site.root_url
        
        # Send email
        send_scan_report_email(
            to_email=user_email,
            first_name=user_name,
            site_name=actual_site_name,
            scan_results=scan_results
        )
        
        logger.info(f"Scan report email sent successfully to {user_email}")
        return {"status": "success", "email_sent_to": user_email}
        
    except Exception as e:
        logger.error(f"Error sending scan completion email: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
