from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.features.waitlist.models.waitlist import Waitlist

async def add_to_waitlist(db: AsyncSession, name: str, email: str):
    entry = Waitlist(name=name, email=email)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry