from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.db.session import get_db
from app.features.waitlist.schemas.waitlist import WaitlistIn, WaitlistOut, WaitlistResponse
from app.features.waitlist.services.waitlist import add_to_waitlist
from app.features.waitlist.utils.emailer import send_thank_you_email


router = APIRouter(prefix="/api/v1", tags=["Waitlist"])

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