import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.platform.db.base import Base
from app.platform.config import DATABASE_URL
from app.platform.db.session import get_db

# Use a test database
TEST_DATABASE_URL = DATABASE_URL.replace("site_audit.db", "test_site_audit.db")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Set up the test database before running tests."""
    # Create test database engine
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Clean up after tests
    await engine.dispose()

@pytest.fixture
async def db_session():
    """Provide a database session for tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False, autocommit=False)

    async with SessionLocal() as session:
        yield session
        await session.rollback() 

@pytest.fixture
def override_get_db(db_session):
    """Override the get_db dependency to use test database"""
    async def override_get_db():
        yield db_session

    return override_get_db