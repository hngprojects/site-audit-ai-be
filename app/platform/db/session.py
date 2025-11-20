from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.platform.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

SessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, autoflush=False, autocommit=False
)

async def get_db():
    async with SessionLocal() as session:
        yield session