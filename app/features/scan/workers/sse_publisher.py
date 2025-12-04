import json
import redis
import logging
from datetime import datetime
from typing import Dict, Any
from app.platform.config import settings

logger = logging.getLogger(__name__)


def publish_sse_event(job_id: str, event_type: str, data: Dict[str, Any]) -> bool:
    try:
        r = redis.from_url(settings.CELERY_RESULT_BACKEND)
        channel = f"scan_progress:{job_id}"
        
        message = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "job_id": job_id,
            **data
        }
        
        r.publish(channel, json.dumps(message))
        logger.info(f"[{job_id}] Published SSE event: {event_type}")
        return True
        
    except Exception as e:
        logger.error(f"[{job_id}] Failed to publish SSE event '{event_type}': {e}")
        return False