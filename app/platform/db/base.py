import uuid
import sqlalchemy
import sqlalchemy
from sqlalchemy.orm import declarative_base
from sqlalchemy import UUID, Column, String
from uuid_extension import uuid7

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    id = Column(String, primary_key=True, default=lambda: str(uuid7()), index=True)
    created_at = Column(
        sqlalchemy.DateTime(timezone=True), server_default=sqlalchemy.func.now(), nullable=False
    )
    updated_at = Column(
        sqlalchemy.DateTime(timezone=True),
        server_default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
        nullable=False,
    )

# Note: Models will import this Base. Do not import models here to avoid circular imports.
# Import models in alembic/env.py instead for migrations.