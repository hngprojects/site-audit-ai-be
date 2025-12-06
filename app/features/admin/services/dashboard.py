from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.user import User
from app.features.leads.models.lead_model import Lead
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.sites.models.site import Site


class TimePeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AdminDashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(self) -> dict:
        total_leads = await self.db.scalar(select(func.count(Lead.id)))

        active_users = await self.db.scalar(
            select(func.count(User.id)).where(
                User.last_login >= datetime.utcnow() - timedelta(days=30)
            )
        )

        websites_scanned = (
            await self.db.scalar(select(func.count(func.distinct(ScanJob.site_id)))) or 0
        )

        total_users = await self.db.scalar(select(func.count(User.id))) or 0
        conversion_rate = (websites_scanned / total_users * 100) if total_users > 0 else 0.0

        return {
            "total_leads": total_leads or 0,
            "active_users": active_users or 0,
            "websites_scanned": websites_scanned,
            "conversion_rate": round(conversion_rate, 2),
        }

    async def get_real_time_activity(self) -> dict:
        active_scans = (
            await self.db.scalar(
                select(func.count(ScanJob.id)).where(
                    ScanJob.status.in_(
                        [
                            ScanJobStatus.queued,
                            ScanJobStatus.discovering,
                            ScanJobStatus.selecting,
                            ScanJobStatus.scraping,
                            ScanJobStatus.analyzing,
                            ScanJobStatus.aggregating,
                        ]
                    )
                )
            )
            or 0
        )

        total_online_users = (
            await self.db.scalar(
                select(func.count(User.id)).where(
                    User.last_login >= datetime.utcnow() - timedelta(minutes=15)
                )
            )
            or 0
        )

        avg_scan_time_result = await self.db.execute(
            select(
                func.avg(
                    func.extract("epoch", ScanJob.completed_at)
                    - func.extract("epoch", ScanJob.started_at)
                )
            ).where(
                ScanJob.status == ScanJobStatus.completed,
                ScanJob.started_at.isnot(None),
                ScanJob.completed_at.isnot(None),
                ScanJob.started_at >= datetime.utcnow() - timedelta(days=7),
            )
        )
        avg_scan_time = avg_scan_time_result.scalar()
        avg_scan_time_minutes = round(avg_scan_time / 60, 2) if avg_scan_time else None

        todays_leads = (
            await self.db.scalar(
                select(func.count(Lead.id)).where(
                    Lead.created_at
                    >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                )
            )
            or 0
        )

        return {
            "active_scans": active_scans,
            "total_online_users": total_online_users,
            "avg_scan_time": avg_scan_time_minutes,
            "todays_leads": todays_leads,
        }

    async def get_recent_scans(self, page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
        offset = (page - 1) * per_page

        # Get total count first
        total_query = select(func.count(ScanJob.id)).join(Site, ScanJob.site_id == Site.id)
        total = await self.db.scalar(total_query) or 0

        # Get scans with relationships
        query = (
            select(ScanJob, Site, User)
            .join(Site, ScanJob.site_id == Site.id)
            .outerjoin(User, ScanJob.user_id == User.id)
            .order_by(desc(ScanJob.created_at))
            .offset(offset)
            .limit(per_page)
        )

        result = await self.db.execute(query)
        scans_data = result.all()

        scans = []
        for scan_job, site, user in scans_data:
            scan_info = {
                "id": str(scan_job.id),
                "site_url": site.root_url,
                "status": scan_job.status.value,
                "score_overall": scan_job.score_overall,
                "error_message": scan_job.error_message,
                "created_at": scan_job.created_at.isoformat() if scan_job.created_at else None,
                "completed_at": scan_job.completed_at.isoformat()
                if scan_job.completed_at
                else None,
                "user_email": user.email if user else None,
            }
            scans.append(scan_info)

        return scans, total

    async def get_recent_leads(self, page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
        offset = (page - 1) * per_page

        total_result = await self.db.execute(select(func.count(Lead.id)))
        total = total_result.scalar() or 0

        result = await self.db.execute(
            select(Lead).order_by(desc(Lead.created_at)).offset(offset).limit(per_page)
        )
        leads = result.scalars().all()

        leads_data = []
        for lead in leads:
            lead_info = {
                "id": str(lead.id),
                "email": lead.email,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
                "source": getattr(lead, "source", None),
            }
            leads_data.append(lead_info)

        return leads_data, total

    async def get_score_distribution(self) -> dict:
        total_scans = (
            await self.db.scalar(
                select(func.count(ScanJob.id)).where(
                    ScanJob.status == ScanJobStatus.completed, ScanJob.score_overall.isnot(None)
                )
            )
            or 0
        )

        if total_scans == 0:
            return {
                "poor_percentage": 0.0,
                "average_percentage": 0.0,
                "good_percentage": 0.0,
                "total_scans": 0,
                "poor_count": 0,
                "average_count": 0,
                "good_count": 0,
            }

        poor_count = (
            await self.db.scalar(
                select(func.count(ScanJob.id)).where(
                    ScanJob.status == ScanJobStatus.completed, ScanJob.score_overall < 50
                )
            )
            or 0
        )

        average_count = (
            await self.db.scalar(
                select(func.count(ScanJob.id)).where(
                    ScanJob.status == ScanJobStatus.completed,
                    ScanJob.score_overall >= 50,
                    ScanJob.score_overall < 70,
                )
            )
            or 0
        )

        good_count = (
            await self.db.scalar(
                select(func.count(ScanJob.id)).where(
                    ScanJob.status == ScanJobStatus.completed, ScanJob.score_overall >= 70
                )
            )
            or 0
        )

        return {
            "poor_percentage": round((poor_count / total_scans) * 100, 2),
            "average_percentage": round((average_count / total_scans) * 100, 2),
            "good_percentage": round((good_count / total_scans) * 100, 2),
            "total_scans": total_scans,
            "poor_count": poor_count,
            "average_count": average_count,
            "good_count": good_count,
        }

    async def get_scan_activity_chart(self, period: TimePeriod = TimePeriod.WEEKLY) -> dict:
        """
        Get scan activity data for charts based on time period.
        Returns daily data for the specified period with comparison to previous period.
        """
        now = datetime.utcnow()

        if period == TimePeriod.DAILY:
            # Last 7 days
            current_start = now - timedelta(days=7)
            previous_start = now - timedelta(days=14)
            previous_end = current_start
            date_format = func.date(ScanJob.created_at)
            group_by = func.date(ScanJob.created_at)

        elif period == TimePeriod.WEEKLY:
            # Last 4 weeks (Monday to Friday)
            current_start = now - timedelta(weeks=4)
            previous_start = now - timedelta(weeks=8)
            previous_end = current_start
            date_format = func.date_trunc("week", ScanJob.created_at)
            group_by = func.date_trunc("week", ScanJob.created_at)

        else:  # MONTHLY
            # Last 6 months
            current_start = now - timedelta(days=180)
            previous_start = now - timedelta(days=360)
            previous_end = current_start
            date_format = func.date_trunc("month", ScanJob.created_at)
            group_by = func.date_trunc("month", ScanJob.created_at)

        # Current period data
        current_query = (
            select(group_by.label("period"), func.count(ScanJob.id).label("scan_count"))
            .where(ScanJob.created_at >= current_start)
            .where(ScanJob.created_at <= now)
            .group_by(group_by)
            .order_by(group_by)
        )

        current_result = await self.db.execute(current_query)
        current_data = {row.period: row.scan_count for row in current_result}

        # Previous period data for comparison
        previous_query = (
            select(group_by.label("period"), func.count(ScanJob.id).label("scan_count"))
            .where(ScanJob.created_at >= previous_start)
            .where(ScanJob.created_at <= previous_end)
            .group_by(group_by)
        )

        previous_result = await self.db.execute(previous_query)
        previous_data = {row.period: row.scan_count for row in previous_result}

        # Calculate percentage change
        current_total = sum(current_data.values())
        previous_total = sum(previous_data.values())
        percentage_change = 0.0

        if previous_total > 0:
            percentage_change = round(((current_total - previous_total) / previous_total) * 100, 2)

        # Format response
        chart_data = []
        for period, count in current_data.items():
            period_str = period.isoformat() if hasattr(period, "isoformat") else str(period)
            chart_data.append(
                {
                    "period": period_str,
                    "scan_count": count,
                }
            )

        return {
            "period": str(period),
            "chart_data": chart_data,
            "total_scans": current_total,
            "previous_total": previous_total,
            "percentage_change": percentage_change,
            "comparison_period": f"{previous_start.date()} to {previous_end.date()}",
            "current_period": f"{current_start.date()} to {now.date()}",
        }

    async def get_comprehensive_dashboard(self, period: TimePeriod = TimePeriod.WEEKLY) -> dict:
        """
        Get all dashboard data in a single unified endpoint.
        """
        # Get all basic stats
        dashboard_stats = await self.get_dashboard_stats()
        real_time_activity = await self.get_real_time_activity()
        score_distribution = await self.get_score_distribution()
        scan_activity = await self.get_scan_activity_chart(period)

        # Get recent data (limited for dashboard overview)
        recent_scans, _ = await self.get_recent_scans(page=1, per_page=5)
        recent_leads, _ = await self.get_recent_leads(page=1, per_page=5)

        return {
            "dashboard_stats": dashboard_stats,
            "real_time_activity": real_time_activity,
            "score_distribution": score_distribution,
            "scan_activity_chart": scan_activity,
            "recent_scans": recent_scans,
            "recent_leads": recent_leads,
            "period": str(period),
        }
