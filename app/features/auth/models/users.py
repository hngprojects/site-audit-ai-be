from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship

from app.platform.db import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    password = Column(String, nullable=True)  # nullable to support OAuth users
    user_confirmed = Column(Boolean, default=False)

    # Relationships
    oauth_accounts = relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
