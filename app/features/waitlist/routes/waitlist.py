from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.services.email_service import send_welcome_email as send_thank_you_email
from app.features.waitlist.schemas.waitlist import WaitlistIn, WaitlistOut, WaitListResponse
from app.features.waitlist.services.waitlist import add_to_waitlist
from app.platform.db.session import get_db

router = APIRouter()


@router.post("/waitlist", response_model=WaitListResponse, status_code=status.HTTP_201_CREATED)
async def join_waitlist(
    waitlist_in: WaitlistIn, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)
):
    try:
        entry = await add_to_waitlist(db, waitlist_in)
        background_tasks.add_task(send_thank_you_email, waitlist_in.email, waitlist_in.full_name)

        return {
            "status_code": 201,
            "status": "success",
            "message": "Successfully added to waitlist",
            "data": WaitlistOut.model_validate(entry),
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        ) from e
