from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.waitlist.models.waitlist import Waitlist
from app.features.waitlist.schemas.waitlist import WaitlistIn


async def add_to_waitlist(db: AsyncSession, waitlist_in: WaitlistIn):
    email = waitlist_in.email
    full_name = waitlist_in.full_name
    result = await db.execute(select(Waitlist).where(Waitlist.email == email))
    existing_entry = result.scalars().first()
    if existing_entry:
        raise HTTPException(status_code=400, detail="Email already registered")
    entry = Waitlist(
        full_name=full_name,
        email=email,
        what_best_describes_you=waitlist_in.what_best_describes_you,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
