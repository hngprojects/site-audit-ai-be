from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta
from app.features.waitlist.models.waitlist import Waitlist
from app.platform.cache.redis import redis
import json

CACHE_KEY = "waitlist_stats"
CACHE_TTL = 300 
async def add_to_waitlist(db: AsyncSession, name: str, email: str):
    entry = Waitlist(name=name, email=email)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry

async def get_waitlist_stats(db: AsyncSession):
    
    cached = await redis.get(CACHE_KEY)
    if cached:
        return json.loads(cached)

    now = datetime.utcnow()

    
    total_count_result = await db.execute(select(func.count(Waitlist.id)))
    total_count = total_count_result.scalar()

    # Signups in last 24h
    twenty_four_hours_ago = now - timedelta(hours=24)
    recent_count_result = await db.execute(
        select(func.count(Waitlist.id)).where(Waitlist.created_at >= twenty_four_hours_ago)
    )
    recent_count = recent_count_result.scalar()
    signup_rate_per_hour = recent_count / 24

    stats = {
        "total_signups": total_count,
        "signup_rate_per_hour_last_24h": signup_rate_per_hour
    }

    # Cache the result
    await redis.set(CACHE_KEY, json.dumps(stats), ex=CACHE_TTL)
    return stats