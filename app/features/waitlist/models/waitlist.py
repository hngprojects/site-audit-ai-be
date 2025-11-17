from sqlalchemy import Column, Integer, String
from app.platform.db.base import Base

class Waitlist(Base):
    __tablename__ = "waitlist"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)