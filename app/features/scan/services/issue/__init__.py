"""
Issue service module.

Provides functions for fetching and formatting scan issues.
"""
from app.features.scan.services.issue.issue_service import (
    get_issues_for_job,
    get_issue_by_id,
    format_issue_summary,
    format_issue_detail,
    count_issues_by_severity
)

__all__ = [
    "get_issues_for_job",
    "get_issue_by_id",
    "format_issue_summary",
    "format_issue_detail",
    "count_issues_by_severity"
]
