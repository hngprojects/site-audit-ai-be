from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.platform.config import settings

# Create the async database engine using the DATABASE_URL from settings
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

# Create an async session factory for database operations
SessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, autoflush=False, autocommit=False
)

# Dependency generator for getting a database session (FastAPI style)
async def get_db():
    # Creates a new session for each request and ensures it closes automatically
    async with SessionLocal() as session:
        yield session
