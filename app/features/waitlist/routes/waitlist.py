from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.db.session import get_db
from app.features.waitlist.schemas.waitlist import WaitlistIn, WaitlistOut, WaitlistResponse
from app.features.waitlist.services.waitlist import add_to_waitlist,get_waitlist_stats
from app.features.waitlist.utils.emailer import send_thank_you_email
from fastapi.responses import JSONResponse
router = APIRouter( tags=["Waitlist"])

@router.post("/waitlist", response_model=WaitlistResponse)
async def join_waitlist(
    waitlist_in: WaitlistIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        entry = await add_to_waitlist(db, waitlist_in.name, waitlist_in.email)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email already registered or DB error.")
    background_tasks.add_task(send_thank_you_email, waitlist_in.email, waitlist_in.name)
    return WaitlistResponse(
        status_code=201,
        success=True,
        message="Waitlist entry created",
        data=WaitlistOut.from_orm(entry)
    )

# GET /waitlist/stats
@router.get("/waitlist/stats")
async def waitlist_stats(db: AsyncSession = Depends(get_db)):
    stats = await get_waitlist_stats(db)
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "status_code": 200,
            "message": "Waitlist statistics retrieved",
            "data": stats
        }
    )