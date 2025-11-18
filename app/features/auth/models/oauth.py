from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.platform.db import BaseModel


class OAuthAccount(BaseModel):
    __tablename__ = "oauth_accounts"
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String, nullable=False)
    provider_user_id = Column(String, nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    profile_data = Column(JSONB, nullable=True)

    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        # Unique constraint on provider + provider_user_id
        # Same Google account can't be linked twice
        Index("idx_provider_user", "provider", "provider_user_id", unique=True),
    )
