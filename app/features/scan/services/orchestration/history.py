from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List

from app.features.scan.models.scan_job import ScanJob as Scan
from app.features.scan.schemas.scan import ScanHistoryItem

import logging 

logger = logging.getLogger(__name__)

async def get_user_scan_history(user_id: str, db: AsyncSession, limit: int = 50) -> List[ScanHistoryItem]:
    try:
        query = (
            select(Scan)
            .where(Scan.user_id == user_id)
            .options(selectinload(Scan.site))  # Eagerly load the site relationship
            .order_by(desc(Scan.created_at))
            .limit(limit)
        )
        result = await db.execute(query)
        scans = result.scalars().all()
        
        logger.info(f"Found {len(scans)} scans for user {user_id}")
        
        # Manually convert to schema to handle enum and relationship properly
        history_items = []
        for scan in scans:
            history_items.append(
                ScanHistoryItem(
                    id=scan.id,
                    status=scan.status.value if hasattr(scan.status, 'value') else str(scan.status),
                    created_at=scan.created_at,
                    completed_at=scan.completed_at,
                    site={
                        "id": scan.site.id if scan.site else None,
                        "root_url": scan.site.root_url if scan.site else "Unknown"
                    }
                )
            )
        
        return history_items
        
    except Exception as e:
        logger.error(f"Failed to fetch history for user {user_id}: {str(e)}")
        raise e