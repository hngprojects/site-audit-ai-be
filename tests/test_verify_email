import pytest
from datetime import datetime, timedelta
from app.features.auth.models.verify_email import EmailVerification
from app.features.auth.services.verify_email import EmailVerificationService

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from collections.abc import AsyncGenerator

from app.platform.config import DATABASE_URL
from app.platform.db.session import SessionLocal

pytestmark = pytest.mark.anyio(backend="asyncio")

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # 1. Create a fresh engine for this specific test
    # NullPool is important: it forces connections to close immediately after use
    test_engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)
    
    # 2. Create a session factory bound to this new engine
    TestSessionLocal = async_sessionmaker(
        bind=test_engine, 
        expire_on_commit=False, 
        autoflush=False
    )
    
    # 3. Create the session
    async with TestSessionLocal() as session:
        yield session
        await session.close()

    # 4. Clean up the engine so it doesn't hang on to the old loop
    await test_engine.dispose()


# Use AnyIO instead of asyncio for Windows stability
@pytest.mark.anyio
async def test_verify_email_code_success(db_session: AsyncSession):
    record = EmailVerification(
        email="test@example.com",
        code="123456",
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db_session.add(record)
    await db_session.commit()

    response = await EmailVerificationService.verify_code(
        db_session, "test@example.com", "123456"
    )

    assert response["success"] is True
    assert "temp_token" in response

@pytest.mark.anyio
async def test_verify_email_code_invalid(db_session: AsyncSession):
    record = EmailVerification(
        email="test@example.com",
        code="123456",
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db_session.add(record)
    await db_session.commit()

    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await EmailVerificationService.verify_code(
            db_session, "test@example.com", "wrongcode"
        )

@pytest.mark.anyio
async def test_verify_email_code_expired(db_session: AsyncSession):
    record = EmailVerification(
        email="test@example.com",
        code="123456",
        expires_at=datetime.utcnow() - timedelta(minutes=1)
    )
    db_session.add(record)
    await db_session.commit()

    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await EmailVerificationService.verify_code(
            db_session, "test@example.com", "123456"
        )
