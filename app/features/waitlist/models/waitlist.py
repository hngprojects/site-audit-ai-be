from sqlalchemy import Column, String

from app.platform.db.base import BaseModel


class Waitlist(BaseModel):
    __tablename__ = "waitlist"
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
