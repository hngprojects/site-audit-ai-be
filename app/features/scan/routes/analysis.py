from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any
import logging
import json

from app.features.scan.schemas.scan import AnalysisRequest, AnalysisResponse
from app.features.scan.services.analysis.page_analyzer import PageAnalyzerService
from app.features.scan.models.scan_job import ScanJob, ScanJobStatus
from app.features.scan.models.scan_page import ScanPage
from app.features.scan.models.scan_issue import ScanIssue, IssueCategory, IssueSeverity
from app.platform.response import api_response
from app.platform.db.session import get_db
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan/analysis", tags=["scan-analysis"])


class TestAnalysisRequest(BaseModel):
    """Request for testing analysis without database"""
    extractor_data: Dict[Any, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "extractor_data": {
                    "status_code": 200,
                    "status": "success",
                    "message": "Data extracted",
                    "data": {
                        "metadata_data": {
                            "url": "https://example.com",
                            "title": {"value": "Example", "length": 7, "is_valid": False, "issues": []},
                            "description": {"value": "Example site", "length": 12, "is_valid": False, "issues": []},
                            "has_title": True,
                            "has_description": True,
                            "overall_valid": False,
                            "total_issues": 2
                        },
                        "heading_data": {"h1": ["Example"], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []},
                        "images_data": [],
                        "issues_data": {
                            "images_missing_alt": [],
                            "inputs_missing_label": [],
                            "buttons_missing_label": [],
                            "links_missing_label": [],
                            "empty_headings": []
                        },
                        "text_content_data": {
                            "word_count": 50,
                            "header_body_ratio": 0.1,
                            "readability_score": 65.5,
                            "keyword_analysis": {}
                        }
                    }
                }
            }
        }


@router.post("/test", summary="Test analysis without database")
async def test_analysis(data: TestAnalysisRequest):
    """
    Test the PageAnalyzerService directly without database.
    
    This endpoint allows you to test the LLM analysis by providing
    mock extractor data directly. Useful for testing the OpenRouter integration.
    
    ⚠️ WARNING: This endpoint can take 5-10 minutes to complete due to:
    - Complex analysis prompt with comprehensive page data
    - Structured JSON schema requirements
    - LLM processing time on OpenRouter
    
    For production, use Celery workers to process pages asynchronously.
    
    Args:
        data: TestAnalysisRequest with extractor_data
        
    Returns:
        Analysis results from PageAnalyzerService
    """
    try:
        logger.info("Testing PageAnalyzerService with provided extractor data")
        
        # Call PageAnalyzerService directly
        analysis_result = PageAnalyzerService.analyze_page(data.extractor_data)
        
        logger.info(f"Analysis complete: Overall score {analysis_result.get('overall_score')}/100")
        
        return api_response(
            data=analysis_result,
            message="Analysis completed successfully"
        )
        
    except Exception as e:
        logger.error(f"Test analysis failed: {str(e)}", exc_info=True)
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Analysis failed: {str(e)}",
            data={}
        )


@router.post("", response_model=AnalysisResponse)
async def analyze_pages(
    data: AnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze scraped pages for issues using LLM.
    
    This endpoint:
    - Fetches ScanPage records with extracted data (analysis_details field)
    - Calls PageAnalyzerService to analyze each page using OpenRouter LLM
    - Creates ScanIssue records for each finding
    - Updates ScanPage with scores and analysis results
    - Updates ScanJob status
    
    Args:
        data: AnalysisRequest with page_ids to analyze
        db: Database session
        
    Returns:
        AnalysisResponse with found issues
    """
    try:
        logger.info(f"Starting analysis for job_id={data.job_id}, {len(data.page_ids)} pages")
        
        total_issues = 0
        pages_analyzed = 0
        
        # Fetch pages to analyze
        result = await db.execute(
            select(ScanPage).where(ScanPage.id.in_(data.page_ids))
        )
        pages = result.scalars().all()
        
        if not pages:
            logger.warning(f"No pages found with provided page_ids: {data.page_ids}")
            return api_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No pages found with provided IDs",
                data={"issues_found": 0, "pages_analyzed": 0, "job_id": data.job_id}
            )
        
        logger.info(f"Found {len(pages)} pages to analyze")
        
        for page in pages:
            try:
                # Check if page has extracted data in analysis_details
                if not page.analysis_details:
                    logger.warning(f"Page {page.id} ({page.page_url}) missing analysis_details, skipping. "
                                 f"Make sure the scraping/extraction phase populated this field.")
                    continue
                
                logger.info(f"Page {page.id} has analysis_details, proceeding with analysis")
                
                # The analysis_details should contain the extractor service response
                extractor_response = page.analysis_details
                
                # Call PageAnalyzerService to analyze
                logger.info(f"Analyzing page: {page.page_url}")
                analysis_result = PageAnalyzerService.analyze_page(extractor_response)
                
                # Update ScanPage with scores and structured analysis
                page.score_overall = analysis_result.get("overall_score")
                page.score_seo = analysis_result.get("seo", {}).get("score")
                page.score_accessibility = analysis_result.get("ux", {}).get("score")  # UX maps to accessibility
                page.score_performance = analysis_result.get("performance", {}).get("score")
                page.analysis_details = analysis_result  # Store full structured analysis
                
                # Create ScanIssue records for each problem found
                issue_count = 0
                
                # Process UX/Accessibility issues
                for problem in analysis_result.get("ux", {}).get("problems", []):
                    issue = ScanIssue(
                        scan_page_id=page.id,
                        scan_job_id=page.scan_job_id,
                        category=IssueCategory.accessibility,
                        severity=IssueSeverity.warning if problem.get("icon") == "warning" else IssueSeverity.critical,
                        title=problem.get("title", "Unknown Issue"),
                        description=problem.get("description", ""),
                        recommendation=analysis_result.get("ux", {}).get("impact_message", "")
                    )
                    db.add(issue)
                    issue_count += 1
                
                # Process Performance issues
                for problem in analysis_result.get("performance", {}).get("problems", []):
                    issue = ScanIssue(
                        scan_page_id=page.id,
                        scan_job_id=page.scan_job_id,
                        category=IssueCategory.performance,
                        severity=IssueSeverity.warning if problem.get("icon") == "warning" else IssueSeverity.critical,
                        title=problem.get("title", "Unknown Issue"),
                        description=problem.get("description", ""),
                        recommendation=analysis_result.get("performance", {}).get("impact_message", "")
                    )
                    db.add(issue)
                    issue_count += 1
                
                # Process SEO issues
                for problem in analysis_result.get("seo", {}).get("problems", []):
                    issue = ScanIssue(
                        scan_page_id=page.id,
                        scan_job_id=page.scan_job_id,
                        category=IssueCategory.seo,
                        severity=IssueSeverity.warning if problem.get("icon") == "warning" else IssueSeverity.critical,
                        title=problem.get("title", "Unknown Issue"),
                        description=problem.get("description", ""),
                        recommendation=analysis_result.get("seo", {}).get("impact_message", "")
                    )
                    db.add(issue)
                    issue_count += 1
                
                # Update page issue counts
                page.critical_issues_count = sum(
                    1 for p in analysis_result.get("ux", {}).get("problems", []) + 
                              analysis_result.get("performance", {}).get("problems", []) + 
                              analysis_result.get("seo", {}).get("problems", [])
                    if p.get("icon") == "alert"
                )
                page.warning_issues_count = issue_count - page.critical_issues_count
                
                total_issues += issue_count
                pages_analyzed += 1
                
                logger.info(f"Page {page.page_url} analyzed: {issue_count} issues, score {page.score_overall}/100")
                
            except Exception as page_err:
                logger.error(f"Failed to analyze page {page.id}: {str(page_err)}", exc_info=True)
                continue
        
        # Update ScanJob if job_id provided
        if data.job_id:
            await db.execute(
                update(ScanJob)
                .where(ScanJob.id == data.job_id)
                .values(
                    pages_llm_analyzed=pages_analyzed,
                    total_issues=total_issues,
                    status=ScanJobStatus.analyzing
                )
            )
        
        await db.commit()
        logger.info(f"Analysis complete: {pages_analyzed} pages, {total_issues} issues found")
        
        return api_response(
            data={
                "issues_found": total_issues,
                "pages_analyzed": pages_analyzed,
                "job_id": data.job_id,
                "message": f"Successfully analyzed {pages_analyzed} pages"
            }
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        
        # Mark job as failed if job_id provided
        if data.job_id:
            try:
                await db.execute(
                    update(ScanJob)
                    .where(ScanJob.id == data.job_id)
                    .values(
                        status=ScanJobStatus.failed,
                        error_message=f"Page analysis failed: {str(e)}"
                    )
                )
                await db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update job status: {str(db_err)}")
        
        return api_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Analysis failed: {str(e)}",
            data={}
        )
