from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
from typing import Optional

from app.features.scan.models.device_session import DeviceSession, Platform
from app.platform.utils.device import hash_device_id
from app.platform.logger import get_logger

logger = get_logger(__name__)


async def get_or_create_device_session(
    db: AsyncSession,
    device_id: str,
    platform: Optional[str] = None,
    user_agent: Optional[str] = None,
    user_id: Optional[str] = None
) -> DeviceSession:
    """
    Get existing DeviceSession or create new one for device tracking and rate limiting.

    Returns:
        DeviceSession instance
    """
    device_hash = hash_device_id(device_id)
    
    # Try to find existing session
    query = select(DeviceSession).where(DeviceSession.device_hash == device_hash)
    result = await db.execute(query)
    device_session = result.scalar_one_or_none()
    
    if device_session:
        device_session.last_seen_at = datetime.utcnow()
        
        # Link to user if they just authenticated (migration from anonymous to auth)
        if user_id and not device_session.user_id:
            device_session.user_id = user_id
            logger.info(f"Linked device {device_hash[:8]}... to user {user_id}")
        
        await db.flush()
        return device_session
    
    # Create new device session
    platform_enum = None
    if platform:
        try:
            platform_enum = Platform[platform.lower()]
        except KeyError:
            logger.warning(f"Unknown platform '{platform}', defaulting to None")
            platform_enum = None
    
    device_session = DeviceSession(
        device_hash=device_hash,
        user_id=user_id,
        platform=platform_enum,
        user_agent=user_agent,
        daily_scan_count=0,
        quota_remaining=15,  # Default quota
        total_scans=0
    )
    db.add(device_session)
    await db.flush()
    
    logger.info(f"Created DeviceSession: {device_hash[:8]}... (platform={platform}, user_id={user_id})")
    return device_session


async def check_rate_limit(
    db: AsyncSession,
    device_session: Optional[DeviceSession],
    user_id: Optional[str],
    is_ip_fallback: bool = False
) -> tuple[bool, int, str]:
    """
    Check if the request should be rate limited.
    
    Rate limits:
    - Authenticated users (user_id): 15 scans/day
    - Anonymous mobile (device_id): 5 scans/day
    - IP fallback: 3 scans/day (stricter for security)
    
    Returns:
        (is_allowed, remaining_quota, message) tuple
    """
    if not device_session:
        # Should not happen, but handle gracefully
        return True, 0, "No device session"
    
    # Reset daily counter if it's a new day
    today = date.today()
    last_scan_date = device_session.last_scan_date
    
    if last_scan_date is None or last_scan_date.date() < today:
        if user_id:
            device_session.daily_scan_count = 0
            device_session.quota_remaining = 15
        elif is_ip_fallback:
            device_session.daily_scan_count = 0
            device_session.quota_remaining = 3
        else:
            device_session.daily_scan_count = 0
            device_session.quota_remaining = 5
        
        await db.flush()
        logger.info(f"Reset daily quota for device {device_session.device_hash[:8]}... "
                   f"(quota={device_session.quota_remaining}, user_id={user_id}, ip_fallback={is_ip_fallback})")
    
    # Check if quota exceeded
    if device_session.quota_remaining <= 0:
        logger.warning(f"Rate limit exceeded for device {device_session.device_hash[:8]}... "
                      f"(daily_count={device_session.daily_scan_count}, user_id={user_id})")
        return False, 0, "Daily scan limit reached"
    
    return True, device_session.quota_remaining, "OK"


async def increment_scan_count(
    db: AsyncSession,
    device_session: DeviceSession
) -> None:
    """
    Increment the scan counters for the device session.
    
    Args:
        db: Database session
        device_session: DeviceSession to update
    """
    device_session.daily_scan_count += 1
    device_session.quota_remaining -= 1
    device_session.total_scans += 1
    device_session.last_scan_date = datetime.utcnow()
    
    await db.flush()
    
    logger.info(f"Incremented scan count for device {device_session.device_hash[:8]}... "
               f"(daily={device_session.daily_scan_count}, remaining={device_session.quota_remaining})")
