from sqlalchemy import Column, Integer, String ,  DateTime, func
from app.platform.db.base import Base, BaseModel

class Waitlist(BaseModel):
    __tablename__ = "waitlist"
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)