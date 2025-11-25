from sqlalchemy import JSON, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.platform.db.base import BaseModel


class OAuthAccount(BaseModel):
    __tablename__ = "oauth_accounts"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=False, index=True)
    provider_email = Column(String(255), nullable=True)
    provider_data = Column(JSON, nullable=True) 

    user = relationship("User", backref="oauth_accounts")

    def __repr__(self):
        return f"<OAuthAccount(user_id={self.user_id}, provider={self.provider})>"
