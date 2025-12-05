import json
import hashlib
from typing import Optional, Tuple
from fastapi import Request
from app.platform.logger import get_logger

logger = get_logger(__name__)


def parse_device_header(request: Request) -> Tuple[Optional[str], Optional[str]]:
   
    x_device_header = request.headers.get("x-device")
    
    if not x_device_header:
        logger.debug("X-Device header not present")
        return None, None
    
    try:
        device_data = json.loads(x_device_header)
        device_id = device_data.get("deviceId")
        platform = device_data.get("device", "unknown")
        
        if not device_id:
            logger.warning("X-Device header present but deviceId field is empty")
            return None, None
        
        logger.info(f"Parsed X-Device header: device_id={device_id[:8]}..., platform={platform}")
        return device_id, platform
        
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"Failed to parse X-Device header '{x_device_header}': {e}")
        return None, None


def generate_ip_fingerprint(request: Request) -> str:
    # Used when neither user_id nor device_id is available (error case/web).
    client_ip = request.client.host if request.client else "unknown"
    
    ip_hash = hashlib.sha256(f"{client_ip}:sitelytics-salt".encode()).hexdigest()[:16]
    
    logger.warning(f"Using IP-based fallback identifier: ip-{ip_hash} (client_ip={client_ip})")
    
    return f"ip-{ip_hash}"


def hash_device_id(device_id: str) -> str:
    return hashlib.sha256(device_id.encode()).hexdigest()
