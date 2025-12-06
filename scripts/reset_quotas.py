import asyncio
from app.platform.db.session import SessionLocal
from app.features.scan.models.device_session import DeviceSession
from sqlalchemy import update

async def reset_quotas():
    async with SessionLocal() as db:
        # Reset all quotas to new limits
        await db.execute(
            update(DeviceSession)
            .values(
                daily_scan_count=0,
                quota_remaining=20  # Set to new max
            )
        )
        await db.commit()
        print("✅ All device quotas have been reset to 20")

asyncio.run(reset_quotas())
