from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.features.waitlist.models.waitlist import Waitlist


async def add_to_waitlist(db: AsyncSession, name: str, email: str):
    result = await db.execute(select(Waitlist).where(Waitlist.email == email))
    existing_entry = result.scalars().first()
    if existing_entry:
        raise HTTPException(status_code=400, detail="Email already registered")
    entry = Waitlist(name=name, email=email)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
