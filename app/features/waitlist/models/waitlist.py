from sqlalchemy import Column, Integer, String, ForeignKey
from app.platform.db.base import Base
from app.platform.db.base import BaseModel


class Waitlist(BaseModel):
    __tablename__ = "waitlist"
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    # referral_code = Column(String, unique=True, nullable=False, index=True)
    # referred_by = Column(String, ForeignKey("waitlist.referral_code"), nullable=True)
    # referral_count = Column(Integer, default=0)
