from app.platform.logger import get_logger
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from app.platform.response import api_response
# Make sure to import the new FullAuditResult if needed for typing, though usually implied
from app.features.audit.services.audit import PageAnalyzer 
from app.features.audit.utils.test_content import page_content
from app.features.audit.schemas.audit import AuditIn, AuditOut, UXOut, SEOOut, SpeedOut

logger = get_logger("audit_routes")
router = APIRouter()

@router.post("/audit", response_model=AuditOut)
async def audit_page(
    audit_in: AuditIn,
    background_tasks: BackgroundTasks,
):
    logger.info(f"Starting audit for URL: {audit_in.url}")

    try:
        analyzer = PageAnalyzer()
        
        # result is now an instance of FullAuditResult
        result = await analyzer.analyze_page(audit_in.url, page_content)

        # 4. Data Mapping (Updated for Object Access)
        # Since result.ux is already a Pydantic model (UXAnalysis), 
        # we can dump it to dict or use it directly if schemas match exactly.
        
        ux_out = UXOut(**result.ux.model_dump())
        seo_out = SEOOut(**result.seo.model_dump())
        speed_out = SpeedOut(**result.speed.model_dump())

        overall = int((ux_out.score + seo_out.score + speed_out.score) / 3)

        audit_result = AuditOut(
            ux=ux_out,
            seo=seo_out,
            speed=speed_out,
            overall_score=overall
        )

        return api_response(
            data=audit_result.model_dump(),
            message="Website Audited",
            status_code=200
        )

    except (ValueError, TypeError) as e:
        logger.warning(f"Validation error for {audit_in.url}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Critical internal error auditing {audit_in.url}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An internal error occurred while processing the audit."
        )