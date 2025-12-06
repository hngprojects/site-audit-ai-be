from sqlalchemy import Boolean, Column, DateTime, String

from app.platform.db.base import BaseModel


class Admin(BaseModel):
    __tablename__ = "admins"

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_super_admin = Column(Boolean, default=False, nullable=False)

    last_login = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)

    def __repr__(self):
        return f"<Admin(id={self.id}, email={self.email}, is_active={self.is_active})>"
