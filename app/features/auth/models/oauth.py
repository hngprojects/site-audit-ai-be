from sqlalchemy import JSON, Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.platform.db.base import BaseModel


class OAuthAccount(BaseModel):
    __tablename__ = "oauth_accounts"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # e.g., "google", "apple"
    provider_user_id = Column(String(255), nullable=False, index=True)  # The "sub" claim from OAuth
    provider_email = Column(String(255), nullable=True)
    provider_data = Column(JSON, nullable=True)  # Store profile data as JSON

    # Relationship to User
    user = relationship("User", backref="oauth_accounts")

    # Constraints to ensure each user has only one account per provider
    __table_args__ = (
        # Ensure user can have only one connection per provider
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
        # Each provider user ID is unique per provider
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_user")
    )

    def __repr__(self):
        return f"<OAuthAccount(user_id={self.user_id}, provider={self.provider})>"
