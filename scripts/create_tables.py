## quick hack to be removed

from app.platform.db.session import engine
from app.features.waitlist.models.waitlist import Base

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

import asyncio
asyncio.run(create_tables())