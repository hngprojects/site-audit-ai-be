"""
SSE (Server-Sent Events) helper for publishing real-time progress updates via Redis pub/sub.

This module provides utilities for Celery tasks to broadcast scan progress events
that can be consumed by SSE endpoints for real-time client updates.
"""

import json
import logging
from typing import Any, Dict, Optional

import redis

from app.platform.config import settings

logger = logging.getLogger(__name__)

# Redis client for pub/sub
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create a Redis client for pub/sub operations.
    
    Returns:
        Redis client instance
    """
    global _redis_client
    
    if _redis_client is None:
        # Extract Redis URL from Celery result backend
        redis_url = settings.CELERY_RESULT_BACKEND
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        logger.info(f"Initialized Redis client for SSE: {redis_url}")
    
    return _redis_client


def publish_scan_progress(
    job_id: str,
    status: str,
    progress: int,
    message: str,
    **extra_data
) -> bool:
    """
    Publish a scan progress event to Redis for SSE streaming.
    
    This function is called by Celery tasks to broadcast progress updates
    that will be consumed by the SSE endpoint and streamed to clients.
    
    Args:
        job_id: The scan job ID
        status: Current status (queued, discovering, selecting, scraping, analyzing, aggregating, completed, failed)
        progress: Progress percentage (0-100)
        message: Human-readable status message
        **extra_data: Additional data to include in the event (pages_discovered, pages_selected, etc.)
    
    Returns:
        True if published successfully, False otherwise
    
    Example:
        publish_scan_progress(
            job_id="abc123",
            status="discovering",
            progress=25,
            message="Found 45 pages",
            pages_discovered=45
        )
    """
    try:
        redis_client = get_redis_client()
        
        # Create event payload
        event_data = {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": _get_current_timestamp(),
            **extra_data  # Include any additional data
        }
        
        # Channel pattern: scan_progress:{job_id}
        channel = f"scan_progress:{job_id}"
        
        # Publish to Redis
        redis_client.publish(channel, json.dumps(event_data))
        
        logger.debug(f"Published SSE event to {channel}: {message} ({progress}%)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish SSE event for job {job_id}: {e}", exc_info=True)
        return False


def _get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    from datetime import datetime
    return datetime.utcnow().isoformat()


def publish_scan_error(job_id: str, error_message: str) -> bool:
    """
    Publish a scan error event.
    
    Args:
        job_id: The scan job ID
        error_message: Error description
    
    Returns:
        True if published successfully, False otherwise
    """
    return publish_scan_progress(
        job_id=job_id,
        status="failed",
        progress=0,
        message=f"Scan failed: {error_message}",
        error=error_message
    )


def publish_scan_completion(job_id: str, final_score: int, total_issues: int) -> bool:
    """
    Publish a scan completion event.
    
    Args:
        job_id: The scan job ID
        final_score: Overall score (0-100)
        total_issues: Total number of issues found
    
    Returns:
        True if published successfully, False otherwise
    """
    return publish_scan_progress(
        job_id=job_id,
        status="completed",
        progress=100,
        message=f"Scan completed! Score: {final_score}/100",
        score_overall=final_score,
        total_issues=total_issues
    )
