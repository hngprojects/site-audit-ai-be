from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.features.waitlist.models.waitlist import Waitlist
from app.features.waitlist.utils.referral_code_generator import generate_referral_code


async def add_to_waitlist(db: AsyncSession, name: str, email: str, referred_by: str | None = None):
    referral_code = generate_referral_code(10)

    while True:
        result = await db.execute(select(Waitlist).where(Waitlist.referral_code == referral_code))
        existing_code = result.scalars().first()
        if not existing_code:
            break
        referral_code = generate_referral_code()

    entry = Waitlist(
        name=name,
        email=email,
        referral_code=referral_code,
        referred_by=referred_by
    )

    if referred_by:
        result = await db.execute(select(Waitlist).where(Waitlist.referral_code == referred_by))
        referrer = result.scalars().first()
        if referrer:
            referrer.referral_count += 1
            db.add(referrer)

    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
