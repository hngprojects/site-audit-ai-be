from celery import Celery
from kombu import Queue

from app.platform.config import settings


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.
    
    Queue Structure:
    - scan.discovery: Page discovery tasks (Selenium crawling)
    - scan.selection: LLM-based page selection tasks
    - scan.scraping: HTML/content scraping tasks
    - scan.extraction: Data extraction tasks
    - scan.analysis: LLM analysis tasks
    - scan.aggregation: Final score aggregation tasks
    """
    celery_app = Celery(
        "site_audit_ai",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    
    # Task serialization
    celery_app.conf.update(
        task_serializer=settings.CELERY_TASK_SERIALIZER,
        result_serializer=settings.CELERY_RESULT_SERIALIZER,
        accept_content=[settings.CELERY_ACCEPT_CONTENT],
        timezone="UTC",
        enable_utc=True,
        task_track_started=settings.CELERY_TASK_TRACK_STARTED,
        task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
        
        # Result settings
        result_expires=3600,  # Results expire after 1 hour
        
        # Task routing - each phase goes to its dedicated queue
        task_routes={
            "app.features.scan.workers.tasks.discover_pages": {"queue": "scan.discovery"},
            "app.features.scan.workers.tasks.select_pages": {"queue": "scan.selection"},
            "app.features.scan.workers.tasks.scrape_page": {"queue": "scan.scraping"},
            "app.features.scan.workers.tasks.extract_data": {"queue": "scan.extraction"},
            "app.features.scan.workers.tasks.analyze_page": {"queue": "scan.analysis"},
            "app.features.scan.workers.tasks.aggregate_results": {"queue": "scan.aggregation"},
            # Orchestrator task
            "app.features.scan.workers.tasks.run_scan_pipeline": {"queue": "scan.orchestration"},
        },
        
        # Define queues
        task_queues=(
            Queue("default"),
            Queue("scan.orchestration"),
            Queue("scan.discovery"),
            Queue("scan.selection"),
            Queue("scan.scraping"),
            Queue("scan.extraction"),
            Queue("scan.analysis"),
            Queue("scan.aggregation"),
        ),
        
        # Default queue
        task_default_queue="default",
        
        # Concurrency settings (can be overridden per worker)
        worker_prefetch_multiplier=1,  # Fair distribution
        
        # Retry settings
        task_acks_late=True,  # Acknowledge after task completes
        task_reject_on_worker_lost=True,  # Requeue if worker dies
    )
    
    # Auto-discover tasks in the workers module
    celery_app.autodiscover_tasks(["app.features.scan.workers"])
    
    return celery_app


# Global Celery app instance
celery_app = create_celery_app()
