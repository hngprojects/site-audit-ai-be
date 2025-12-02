from sqlalchemy import Column, String
from app.platform.db.base import BaseModel

class Lead(BaseModel):
    __tablename__ = "leads"
    email = Column(String(255), nullable=False, unique=True, index=True)

    def __repr__(self) -> str:
        return f"<Lead(email='{self.email}', source='{self.source}')>"