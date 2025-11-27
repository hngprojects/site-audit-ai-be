from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from app.features.scan.models.scan_job import ScanJob as Scan

import logging 

logger = logging.getLogger(__name__)

async def get_user_scan_history(user_id: str, db: AsyncSession, limit: int = 50) -> List[Scan]:
    try:
        query = (
            select(Scan)
            .where(Scan.user_id == user_id)
            .order_by(desc(Scan.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()
        
    except Exception as e:
        logger.error(f"Failed to fetch history for user {user_id}: {str(e)}")
        raise e