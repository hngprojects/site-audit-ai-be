from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class TimePeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class DashboardStatsResponse(BaseModel):
    total_leads: int
    active_users: int
    websites_scanned: int
    conversion_rate: float


class RealTimeActivityResponse(BaseModel):
    active_scans: int
    total_online_users: int
    avg_scan_time: Optional[float] = None
    todays_leads: int


class ScanInfo(BaseModel):
    id: str
    site_url: str
    status: str
    score_overall: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    user_email: Optional[str] = None


class RecentScansResponse(BaseModel):
    scans: List[ScanInfo]
    total: int
    page: int
    per_page: int
    pages: int


class LeadInfo(BaseModel):
    id: str
    email: str
    created_at: datetime
    source: Optional[str] = None


class RecentLeadsResponse(BaseModel):
    leads: List[LeadInfo]
    total: int
    page: int
    per_page: int
    pages: int


class ScoreDistributionResponse(BaseModel):
    poor_percentage: float  # 0-49
    average_percentage: float  # 50-69
    good_percentage: float  # 70+
    total_scans: int
    poor_count: int
    average_count: int
    good_count: int


class ChartDataPoint(BaseModel):
    period: str
    scan_count: int


class ScanActivityChartResponse(BaseModel):
    period: str
    chart_data: List[ChartDataPoint]
    total_scans: int
    previous_total: int
    percentage_change: float
    comparison_period: str
    current_period: str


class ComprehensiveDashboardResponse(BaseModel):
    dashboard_stats: DashboardStatsResponse
    real_time_activity: RealTimeActivityResponse
    score_distribution: ScoreDistributionResponse
    scan_activity_chart: ScanActivityChartResponse
    recent_scans: List[ScanInfo]
    recent_leads: List[LeadInfo]
    period: str
