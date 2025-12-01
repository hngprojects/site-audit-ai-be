from time import time
from fastapi import HTTPException, status
from typing import Dict, List
from threading import Lock

_requests: Dict[str, List[float]] = {}
_lock = Lock()

WINDOW_SECONDS = 60
MAX_REQUESTS = 10

def rate_limit(key: str):
    now = time()
    with _lock:
        timestamps = _requests.get(key, [])
        # Remove old timestamps outside window
        cutoff = now - WINDOW_SECONDS
        timestamps = [ts for ts in timestamps if ts > cutoff]
        if len(timestamps) >= MAX_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
            )
        timestamps.append(now)
        _requests[key] = timestamps
