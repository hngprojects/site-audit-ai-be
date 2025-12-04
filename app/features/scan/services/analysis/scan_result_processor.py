import logging
from typing import Dict, Any, Optional

from app.features.scan.services.extraction.extractor_service import ExtractorService
from app.features.scan.services.analysis.page_analyzer import PageAnalyzerService
from app.features.scan.services.analysis.scan_result_saver import ScanResultSaver
from app.features.scan.workers.sse_publisher import publish_sse_event

logger = logging.getLogger(__name__)


class ScanResultProcessor:
    
    @staticmethod
    def process_page_scan(
        db,
        job_id: str,
        url: str,
        html_content: str,
        load_time_ms: int,
        page_title: Optional[str] = None
    ) -> Dict[str, Any]:

        try:
            logger.info(f"[{job_id}] Starting result processing for {url}")
            
            logger.info(f"[{job_id}] Extracting content from HTML...")
            extracted_data = ExtractorService.extract_from_html(html_content, url)
            
            logger.info(f"[{job_id}] Analyzing with LLM...")
            analysis_result = PageAnalyzerService.analyze_page(extracted_data)
            
            logger.info(f"[{job_id}] Publishing analysis events...")
            ScanResultProcessor._publish_analysis_events(job_id, analysis_result)
            
            logger.info(f"[{job_id}] Saving results to database...")
            overall_score = ScanResultSaver.save_scan_results(
                db=db,
                job_id=job_id,
                url=url,
                analysis_result=analysis_result,
                load_time_ms=load_time_ms,
                page_title=page_title
            )
            
            logger.info(f"[{job_id}] Publishing completion event...")
            ScanResultProcessor._publish_completion_event(
                job_id=job_id,
                overall_score=overall_score,
                analysis_result=analysis_result
            )
            
            logger.info(f"[{job_id}] Result processing complete. Overall score: {overall_score}")
            
            return {
                "job_id": job_id,
                "overall_score": overall_score,
                "seo_score": analysis_result.seo_score,
                "accessibility_score": analysis_result.usability_score,
                "performance_score": analysis_result.performance_score,
                "total_issues": len(analysis_result.seo_issues) + len(analysis_result.usability_issues) + len(analysis_result.performance_issues),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"[{job_id}] Result processing failed: {e}", exc_info=True)
            
            publish_sse_event(job_id, "scan_error", {
                "progress": 0,
                "message": f"Analysis failed: {str(e)}",
                "error": str(e)
            })
            
            raise
    
    @staticmethod
    def _publish_analysis_events(job_id: str, analysis_result) -> None:
        publish_sse_event(job_id, "seo_check", {
            "progress": 60,
            "score": analysis_result.seo_score,
            "message": f"SEO Score: {analysis_result.seo_score}/100",
            "issues_count": len(analysis_result.seo_issues),
            "top_issues": [
                {
                    "title": issue.title,
                    "severity": issue.severity,
                    "description": issue.description,
                    "recommendation": issue.recommendation,
                    "business_impact": issue.business_impact,
                    "score_impact": issue.score_impact
                }
                for issue in analysis_result.seo_issues[:3]
            ]
        })
        
        publish_sse_event(job_id, "accessibility_check", {
            "progress": 75,
            "score": analysis_result.usability_score,
            "message": f"Accessibility Score: {analysis_result.usability_score}/100",
            "issues_count": len(analysis_result.usability_issues),
            "top_issues": [
                {
                    "title": issue.title,
                    "severity": issue.severity,
                    "description": issue.description,
                    "recommendation": issue.recommendation,
                    "business_impact": issue.business_impact,
                    "score_impact": issue.score_impact
                }
                for issue in analysis_result.usability_issues[:3]
            ]
        })

        publish_sse_event(job_id, "performance_analysis", {
            "progress": 90,
            "score": analysis_result.performance_score,
            "message": f"Performance Score: {analysis_result.performance_score}/100",
            "issues_count": len(analysis_result.performance_issues),
            "top_issues": [
                {
                    "title": issue.title,
                    "severity": issue.severity,
                    "description": issue.description,
                    "recommendation": issue.recommendation,
                    "business_impact": issue.business_impact,
                    "score_impact": issue.score_impact
                }
                for issue in analysis_result.performance_issues[:3]
            ]
        })
    
    @staticmethod
    def _publish_completion_event(job_id: str, overall_score: int, analysis_result) -> None:
        publish_sse_event(job_id, "scan_complete", {
            "progress": 100,
            "job_id": job_id,
            "overall_score": overall_score,
            "message": f"Scan complete! Overall score: {overall_score}/100",
            "scores": {
                "seo": analysis_result.seo_score,
                "accessibility": analysis_result.usability_score,
                "performance": analysis_result.performance_score
            },
            "total_issues": len(analysis_result.seo_issues) + len(analysis_result.usability_issues) + len(analysis_result.performance_issues)
        })