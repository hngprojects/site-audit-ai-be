from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.platform.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=20, 
    max_overflow=30,  # (burst capacity)
    pool_timeout=30, 
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False, autocommit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session
