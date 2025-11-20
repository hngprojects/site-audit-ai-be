from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.platform.db.session import get_db
from app.features.waitlist.schemas.waitlist import WaitlistIn, WaitlistOut, WaitlistResponse
from app.features.waitlist.services.waitlist import add_to_waitlist
from app.features.waitlist.utils.emailer import send_thank_you_email
from app.platform.response import api_response

router = APIRouter()

@router.post("/waitlist")
async def join_waitlist(
    waitlist_in: WaitlistIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    try:
        entry = await add_to_waitlist(db, waitlist_in.name, waitlist_in.email)
        background_tasks.add_task(send_thank_you_email, waitlist_in.email, waitlist_in.name)
        
        return api_response(
            data=WaitlistOut.from_orm(entry),
            message="Successfully added to waitlist",
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered or database error."
        )