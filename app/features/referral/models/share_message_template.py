from sqlalchemy import Boolean, Column, String, Text

from app.platform.db.base import BaseModel


class ShareMessageTemplate(BaseModel):
    __tablename__ = "share_message_templates"

    platform = Column(String(50), unique=True, nullable=False, index=True)
    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
