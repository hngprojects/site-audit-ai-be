from sqlalchemy import Column, Integer, String, Boolean, DateTime

# from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.sql import func
from app.platform.db.base import Base, BaseModel
from datetime import datetime
import uuid


class User(BaseModel):
    __tablename__ = "users"
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(
        String(255), nullable=True
    )  # make nullable to support OAuth-only accounts

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    is_email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    verification_otp = Column(String(6), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)

    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)

    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
