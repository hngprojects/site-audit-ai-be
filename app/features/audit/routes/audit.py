from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.db.session import get_db
from app.platform.response import api_response
from app.features.audit.utils.page_analyzer import PageAnalyzer
from app.features.audit.utils.test_content import page_content
from app.features.audit.schemas.audit import AuditIn, AuditOut, UXOut, SEOOut, SpeedOut

router = APIRouter()


@router.post("/audit", response_model=AuditOut)
async def audit_page(
    audit_in: AuditIn,
    background_tasks: BackgroundTasks,
):
    try:
        print(f"Audit requested for: {audit_in.url}")

        analyzer = PageAnalyzer()

        # Replace page_content with actual page content. Right now, I am using data from a website that I stored.
        ux_task = analyzer.analyze_ux(audit_in.url, page_content)
        seo_task = analyzer.analyze_seo(audit_in.url, page_content)
        speed_task = analyzer.analyze_speed(audit_in.url, page_content)

        ux, seo, speed = await asyncio.gather(ux_task, seo_task, speed_task)

        ux_out = UXOut(**ux.model_dump())
        seo_out = SEOOut(**seo.model_dump())
        speed_out = SpeedOut(**speed.model_dump())

        # Revisit, right now we are using a basic average calculation
        overall = int((ux.score + seo.score + speed.score) / 3)

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

    except Exception as e:
        print("Audit error:", e)
        raise HTTPException(status_code=400, detail="Website Audit failed")
