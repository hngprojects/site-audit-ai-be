from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.services.dashboard import AdminDashboardService, TimePeriod
from app.features.admin.utils.auth import get_current_admin
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/dashboard", tags=["Admin - Dashboard"])


@router.get(
    "/stats",
    summary="Get dashboard statistics",
)
async def get_dashboard_stats(
    current_admin: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    """
    Get overall dashboard statistics including:
    - Total leads
    - Active users
    - Websites scanned
    - Conversion rate
    """
    service = AdminDashboardService(db)
    stats = await service.get_dashboard_stats()

    return api_response(
        data=stats,
        message="Dashboard statistics retrieved successfully",
    )


@router.get(
    "/real-time-activity",
    summary="Get real-time activity data",
)
async def get_real_time_activity(
    current_admin: dict = Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    """
    Get real-time activity data including:
    - Active scans
    - Total online users
    - Average scan time
    - Today's leads
    """
    service = AdminDashboardService(db)
    activity = await service.get_real_time_activity()

    return api_response(
        data=activity,
        message="Real-time activity data retrieved successfully",
    )


@router.get(
    "/recent-scans",
    summary="Get recent scans with status and scores",
)
async def get_recent_scans(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent scans with their status and scores.
    Includes failed scans with error messages.
    """
    service = AdminDashboardService(db)
    scans, total = await service.get_recent_scans(page=page, per_page=per_page)

    return api_response(
        data={
            "scans": scans,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        },
        message="Recent scans retrieved successfully",
    )


@router.get(
    "/recent-leads",
    summary="Get recent leads",
)
async def get_recent_leads(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent leads with pagination.
    """
    service = AdminDashboardService(db)
    leads, total = await service.get_recent_leads(page=page, per_page=per_page)

    return api_response(
        data={
            "leads": leads,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        },
        message="Recent leads retrieved successfully",
    )


@router.get(
    "/score-distribution",
    summary="Get score distribution statistics",
)
async def get_score_distribution(
    db: AsyncSession = Depends(get_db), current_admin: dict = Depends(get_current_admin)
):
    """
    Get score distribution for completed scans:
    - Poor (0-49)
    - Average (50-69)
    - Good (70+)
    """
    service = AdminDashboardService(db)
    distribution = await service.get_score_distribution()

    return api_response(
        data=distribution,
        message="Score distribution retrieved successfully",
    )


@router.get(
    "/scan-activity-chart",
    summary="Get scan activity chart data",
)
async def get_scan_activity_chart(
    period: TimePeriod = Query(
        TimePeriod.WEEKLY, description="Time period: daily, weekly, or monthly"
    ),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """
    Get scan activity data for charts with time period filtering.
    Includes percentage change compared to previous period.
    """
    service = AdminDashboardService(db)
    chart_data = await service.get_scan_activity_chart(period)

    return api_response(
        data=chart_data,
        message="Scan activity chart data retrieved successfully",
    )


@router.get(
    "/comprehensive",
    summary="Get comprehensive dashboard data",
)
async def get_comprehensive_dashboard(
    period: TimePeriod = Query(
        TimePeriod.WEEKLY, description="Time period: daily, weekly, or monthly"
    ),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """
    Get all dashboard data in a single unified endpoint.
    Includes stats, real-time activity, score distribution, chart data, and recent items.
    """
    service = AdminDashboardService(db)
    dashboard_data = await service.get_comprehensive_dashboard(period)

    return api_response(
        data=dashboard_data,
        message="Comprehensive dashboard data retrieved successfully",
    )
