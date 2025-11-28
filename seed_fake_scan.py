import asyncio
from uuid import uuid4
from datetime import datetime
from app.platform.db.session import engine
from app.features.scan.models.scan_job import ScanJob as Scan
from sqlalchemy.orm import sessionmaker

# 1. ADD YOUR USER ID HERE (Get it from the Signup response or database)
USER_ID = "019ac5fd-93bf-7368-9f64-7726995a6a04" 

async def seed_data():
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        fake_scan = Scan(
            id=str(uuid4()),
            user_id=USER_ID,
            url="https://test-site.com",
            status="completed",
            created_at=datetime.now(),
            completed_at=datetime.now()
        )
        session.add(fake_scan)
        await session.commit()
        print("Fake scan added!")

if __name__ == "__main__":
    from sqlalchemy.ext.asyncio import AsyncSession # Import needed inside logic
    asyncio.run(seed_data())