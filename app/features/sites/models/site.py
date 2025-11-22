from sqlalchemy import Column, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.platform.db.base import BaseModel

class Site(BaseModel):
    __tablename__ = "sites"

    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    name = Column(String, nullable=True)

    # Relationships
    user = relationship("User", backref="sites")

    def __repr__(self):
        return f"<Site(id={self.id}, url={self.url}, user_id={self.user_id})>"
