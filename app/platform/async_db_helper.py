"""
Async Database Helper for Celery Tasks

Provides async database session management for use in synchronous Celery tasks
when they need to interact with async services like NotificationService.
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.platform.config import settings

# Create async engine for notifications from Celery tasks
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,  
    max_overflow=10, 
    pool_timeout=30,
    pool_recycle=1800,
)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_async_db():
    """
    Get async database session for use in sync Celery tasks.

    Usage in Celery task:
        import asyncio
        async with get_async_db() as db:
            service = NotificationService(db)
            await service.create_notification(...)

    Or with asyncio.run():
        asyncio.run(send_notification_helper(...))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
