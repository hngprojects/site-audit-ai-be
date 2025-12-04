from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import aliased

from app.features.auth.routes.auth import get_current_user
from app.features.scan.models.scan_job import ScanJob
from app.features.scan.models.scan_page import ScanPage
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("", status_code=200)
async def list_user_scans(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all websites the user has scanned, with the site URL and the date of their latest scan.
    """
    try:
        latest_scan_subq = (
            select(
                ScanJob.site_id,
                func.max(ScanJob.updated_at).label("last_scan_date")
            )
            .where(
                ScanJob.user_id == current_user.id,
                ScanJob.updated_at.isnot(None),
                ScanJob.status == 'completed'
            )
            .group_by(ScanJob.site_id)
        ).subquery()

        latest_scan = aliased(ScanJob)

        stmt = (
            select(
                latest_scan_subq.c.site_id,
                ScanPage.page_url.label("site_url"),
                latest_scan_subq.c.last_scan_date
            )
            .join(
                latest_scan,
                (latest_scan.site_id == latest_scan_subq.c.site_id) &
                (latest_scan.updated_at == latest_scan_subq.c.last_scan_date)
            )
            .join(
                ScanPage,
                ScanPage.scan_job_id == latest_scan.id
            )
            .group_by(
                latest_scan_subq.c.site_id,
                ScanPage.page_url,
                latest_scan_subq.c.last_scan_date
            )
            .order_by(latest_scan_subq.c.last_scan_date.desc())
        )

        result = await db.execute(stmt)
        sites = result.all()

        data = [
            {
                "site_id": site.site_id,
                "site_url": site.site_url,
                "last_scan_date": site.last_scan_date.isoformat() + "Z" if site.last_scan_date else None
            }
            for site in sites
        ]

        return api_response(data=data)

    except Exception as e:
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Error fetching user websites: {str(e)}",
            data={}
        )
