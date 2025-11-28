"""Celery workers module - imports all task modules for autodiscovery."""

# Import all task modules so they're registered with Celery
from app.features.scan.workers import tasks  # noqa: F401
from app.features.scan.workers import periodic_tasks  # noqa: F401
