from uuid import uuid4

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model that provides common fields for all database tables.

    Attributes:
        id (UUID):
            Primary key for the model. Automatically generated using `uuid4`.
            Ensures each record has a universally unique identifier.

        created_at (DateTime):
            Timestamp indicating when the record was created.
            Automatically set by the database using `NOW()` at insert time.
            Timezone-aware.

        updated_at (DateTime):
            Timestamp indicating when the record was last updated.
            Automatically set by the database on both insert and update.
            Timezone-aware.

    Notes:
        - This class is marked as `__abstract__ = True`, meaning SQLAlchemy
          will not create a table for it. Instead, child classes inherit these
          common fields.
    """

    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
