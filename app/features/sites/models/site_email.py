from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.platform.db.base import BaseModel


class SiteEmailAssociation(BaseModel):
    __tablename__ = "site_email_associations"
    site_id = Column(String, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    site = relationship("Site", lazy="joined")
    __table_args__ = (UniqueConstraint("site_id", "email", name="uq_site_email"),)
