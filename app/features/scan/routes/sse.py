"""
SSE (Server-Sent Events) endpoint for real-time scan progress updates.

This module provides a streaming endpoint that pushes scan progress events
to clients as they happen, eliminating the need for polling.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.features.scan.models.scan_job import ScanJob
from app.platform.config import settings
from app.platform.db.session import get_db
from app.platform.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/scan", tags=["scan"])


async def get_redis_pubsub():
    """
    Create an async Redis pub/sub client for SSE.
    
    Returns:
        Async Redis client
    """
    redis_url = settings.CELERY_RESULT_BACKEND
    redis_client = await aioredis.from_url(redis_url, decode_responses=True)
    return redis_client


async def scan_progress_stream(
    job_id: str,
    db: AsyncSession
) -> AsyncGenerator[dict, None]:
    """
    Stream scan progress events for a specific job.
    
    This generator:
    1. Verifies the job exists
    2. Subscribes to Redis pub/sub channel for the job
    3. Yields progress events as they arrive
    4. Automatically closes when scan completes or fails
    
    Args:
        job_id: The scan job ID
        db: Database session
        
    Yields:
        Dict events in SSE format
    """
    # Verify job exists
    job_query = select(ScanJob).where(ScanJob.id == job_id)
    result = await db.execute(job_query)
    job = result.scalar_one_or_none()
    
    if not job:
        logger.error(f"SSE: Job {job_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan job {job_id} not found"
        )
    
    # Send initial status
    status_str = job.status.value if hasattr(job.status, 'value') else str(job.status)
    initial_progress = _calculate_progress(status_str)
    
    yield {
        "event": "progress",
        "data": json.dumps({
            "job_id": job_id,
            "status": status_str,
            "progress": initial_progress,
            "message": _get_status_message(status_str, job),
            "pages_discovered": job.pages_discovered,
            "pages_selected": job.pages_selected,
            "pages_scanned": job.pages_scanned,
        })
    }
    
    # If already completed/failed, send completion event and close
    if status_str in ["completed", "failed"]:
        yield {
            "event": "complete",
            "data": json.dumps({
                "job_id": job_id,
                "status": status_str,
                "final": True
            })
        }
        return
    
    # Subscribe to Redis pub/sub for live updates
    redis_client = await get_redis_pubsub()
    pubsub = redis_client.pubsub()
    channel = f"scan_progress:{job_id}"
    
    try:
        await pubsub.subscribe(channel)
        logger.info(f"SSE: Subscribed to {channel}")
        
        # Listen for messages with timeout
        timeout = 300  # 5 minutes max connection time
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                logger.info(f"SSE: Connection timeout for job {job_id}")
                yield {
                    "event": "timeout",
                    "data": json.dumps({"message": "Connection timeout"})
                }
                break
            
            try:
                # Wait for message with short timeout for heartbeat
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=30.0
                )
                
                if message and message['type'] == 'message':
                    event_data = json.loads(message['data'])
                    event_status = event_data.get('status')
                    
                    # Yield progress event
                    yield {
                        "event": "progress",
                        "data": json.dumps(event_data)
                    }
                    
                    # If scan completed or failed, send completion event and close
                    if event_status in ["completed", "failed"]:
                        yield {
                            "event": "complete",
                            "data": json.dumps({
                                "job_id": job_id,
                                "status": event_status,
                                "final": True
                            })
                        }
                        break
                else:
                    # Send heartbeat to keep connection alive
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})
                    }
                    
            except asyncio.TimeoutError:
                # No message received, send heartbeat
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"timestamp": asyncio.get_event_loop().time()})
                }
                continue
                
    except Exception as e:
        logger.error(f"SSE: Error streaming for job {job_id}: {e}", exc_info=True)
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)})
        }
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis_client.close()
        logger.info(f"SSE: Closed connection for job {job_id}")


def _calculate_progress(status: str) -> int:
    """Calculate progress percentage based on status."""
    progress_map = {
        "queued": 0,
        "discovering": 10,
        "selecting": 30,
        "scraping": 40,
        "analyzing": 60,
        "aggregating": 90,
        "completed": 100,
        "failed": 0,
    }
    return progress_map.get(status, 0)


def _get_status_message(status: str, job: ScanJob) -> str:
    """Get human-readable status message."""
    messages = {
        "queued": "Waiting to start",
        "discovering": "Finding pages on site",
        "selecting": f"Selecting important pages from {job.pages_discovered or 0} discovered",
        "scraping": f"Scraping {job.pages_selected or 0} pages",
        "analyzing": "Analyzing content",
        "aggregating": "Calculating final scores",
        "completed": "Scan complete",
        "failed": "Scan failed",
    }
    return messages.get(status, "Processing")


@router.get(
    "/{job_id}/stream",
    summary="Stream scan progress (SSE)",
    description="""
    Stream real-time scan progress updates using Server-Sent Events (SSE).
    
    This endpoint establishes a persistent connection and pushes progress updates
    as they happen, eliminating the need for polling.
    
    **Event Types:**
    - `progress`: Scan progress update with status, percentage, and message
    - `complete`: Scan completed or failed (connection will close)
    - `heartbeat`: Keep-alive ping (sent every 30 seconds)
    - `timeout`: Connection timeout (after 5 minutes)
    - `error`: Error occurred
    
    **Progress Event Data:**
    ```json
    {
        "job_id": "abc123",
        "status": "analyzing",
        "progress": 60,
        "message": "Analyzing content",
        "pages_discovered": 45,
        "pages_selected": 10,
        "pages_scanned": 8
    }
    ```
    
    **Client Usage (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/api/v1/scan/{job_id}/stream');
    
    eventSource.addEventListener('progress', (e) => {
        const data = JSON.parse(e.data);
        console.log(`Progress: ${data.progress}% - ${data.message}`);
    });
    
    eventSource.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data);
        console.log(`Scan ${data.status}`);
        eventSource.close();
    });
    ```
    
    Args:
        job_id: The scan job ID
        db: Database session
        
    Returns:
        EventSourceResponse with real-time progress events
    """
)
async def stream_scan_progress(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Stream scan progress events for a specific job using SSE.
    
    Clients can connect to this endpoint and receive real-time updates
    as the scan progresses through its phases.
    """
    logger.info(f"SSE: Client connected for job {job_id}")
    
    return EventSourceResponse(
        scan_progress_stream(job_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
