from sqlalchemy import Column, Integer, String, ForeignKey
from app.platform.db.base import Base

class Waitlist(Base):
    __tablename__ = "waitlist"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    referral_code = Column(String, unique=True, nullable=False, index=True)
    referred_by = Column(String, ForeignKey("waitlist.referral_code"), nullable=True)
    referral_count = Column(Integer, default=0)