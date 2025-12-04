import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.features.scan.models.scan_issue import ScanIssue, IssueCategory, IssueSeverity
from app.features.scan.schemas.page_analyzer import PageAnalysisResult

logger = logging.getLogger(__name__)


class ScanResultSaver:
    
    @staticmethod
    def save_scan_results(
        db: Session,
        job_id: str,
        url: str,
        analysis_result: PageAnalysisResult,
        load_time_ms: int,
        page_title: Optional[str] = None
    ) -> int:
        
        try:
            overall_score = int((
                analysis_result.seo_score +
                analysis_result.usability_score +
                analysis_result.performance_score
            ) / 3)
            
            job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            scan_page = ScanPage(
                scan_job_id=job_id,
                page_url=url,
                page_url_normalized=url.rstrip('/'),
                page_title=page_title or analysis_result.url,
                score_overall=overall_score,
                score_seo=analysis_result.seo_score,
                score_accessibility=analysis_result.usability_score,
                score_performance=analysis_result.performance_score,
                load_time_ms=load_time_ms,
                is_selected_by_llm=True,
                analysis_details={
                    "seo_issues": [
                        {
                            "title": issue.title,
                            "severity": issue.severity,
                            "description": issue.description,
                            "score_impact": issue.score_impact,
                            "business_impact": issue.business_impact,
                            "recommendation": issue.recommendation
                        }
                        for issue in analysis_result.seo_issues
                    ],
                    "usability_issues": [
                        {
                            "title": issue.title,
                            "severity": issue.severity,
                            "description": issue.description,
                            "score_impact": issue.score_impact,
                            "business_impact": issue.business_impact,
                            "recommendation": issue.recommendation
                        }
                        for issue in analysis_result.usability_issues
                    ],
                    "performance_issues": [
                        {
                            "title": issue.title,
                            "severity": issue.severity,
                            "description": issue.description,
                            "score_impact": issue.score_impact,
                            "business_impact": issue.business_impact,
                            "recommendation": issue.recommendation
                        }
                        for issue in analysis_result.performance_issues
                    ]
                },
                scanned_at=datetime.utcnow()
            )
            db.add(scan_page)
            db.flush()
            
            for issue in analysis_result.seo_issues:
                scan_issue = ScanIssue(
                    scan_page_id=scan_page.id,
                    scan_job_id=job_id,
                    category=IssueCategory.seo,
                    severity=IssueSeverity[issue.severity],
                    title=issue.title,
                    description=issue.description,
                    recommendation=issue.recommendation,
                    business_impact=issue.business_impact
                )
                db.add(scan_issue)
            
            for issue in analysis_result.usability_issues:
                scan_issue = ScanIssue(
                    scan_page_id=scan_page.id,
                    scan_job_id=job_id,
                    category=IssueCategory.accessibility,
                    severity=IssueSeverity[issue.severity],
                    title=issue.title,
                    description=issue.description,
                    recommendation=issue.recommendation,
                    business_impact=issue.business_impact
                )
                db.add(scan_issue)
            
            for issue in analysis_result.performance_issues:
                scan_issue = ScanIssue(
                    scan_page_id=scan_page.id,
                    scan_job_id=job_id,
                    category=IssueCategory.performance,
                    severity=IssueSeverity[issue.severity],
                    title=issue.title,
                    description=issue.description,
                    recommendation=issue.recommendation,
                    business_impact=issue.business_impact
                )
                db.add(scan_issue)
            
            total_issues = len(analysis_result.seo_issues) + len(analysis_result.usability_issues) + len(analysis_result.performance_issues)
            critical_count = sum(1 for issue in analysis_result.seo_issues + analysis_result.usability_issues + analysis_result.performance_issues if issue.severity == "high")
            warning_count = sum(1 for issue in analysis_result.seo_issues + analysis_result.usability_issues + analysis_result.performance_issues if issue.severity == "medium")
            
            scan_page.critical_issues_count = critical_count
            scan_page.warning_issues_count = warning_count
            
            job.score_overall = overall_score
            job.score_seo = analysis_result.seo_score
            job.score_accessibility = analysis_result.usability_score
            job.score_performance = analysis_result.performance_score
            job.status = ScanJobStatus.completed
            job.completed_at = datetime.utcnow()
            job.pages_scanned = 1
            job.pages_llm_analyzed = 1
            job.pages_discovered = 1
            job.pages_selected = 1
            job.total_issues = total_issues
            job.critical_issues_count = critical_count
            job.warning_issues_count = warning_count
            
            db.commit()
            
            logger.info(f"[{job_id}] Saved scan results: overall={overall_score}, seo={analysis_result.seo_score}, accessibility={analysis_result.usability_score}, performance={analysis_result.performance_score}, issues={total_issues}")
            
            return overall_score
            
        except Exception as e:
            db.rollback()
            logger.error(f"[{job_id}] Failed to save scan results: {e}", exc_info=True)
            raise