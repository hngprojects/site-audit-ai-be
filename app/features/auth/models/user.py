from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.sql import func
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from sqlalchemy.orm import relationship

from app.platform.db.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(
        String(255), nullable=True
    ) 

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)

    is_email_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    verification_otp = Column(String(6), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    otp_resend_count = Column(Integer, default=0)
    otp_last_resent_at = Column(DateTime, nullable=True)

    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)

    last_login = Column(DateTime, nullable=True)

    sites = relationship("Site", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
