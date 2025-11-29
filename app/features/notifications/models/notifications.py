import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.platform.db.base import BaseModel


class NotificationType(str, enum.Enum):
    """Types of notifications"""

    SCAN_COMPLETE = "scan_complete"
    SCAN_FAILED = "scan_failed"
    ISSUE_DETECTED = "issue_detected"
    ACCOUNT_UPDATE = "account_update"
    SYSTEM_ALERT = "system_alert"
    SUPPORT_RESPONSE = "support_response"


class NotificationPriority(str, enum.Enum):
    """Priority levels for notifications"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    notification_type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Optional link to relevant resource
    action_url = Column(String(500), nullable=True)

    meta = Column(Text, nullable=True)

    is_read = Column(Boolean, default=False, index=True)

    read_at = Column(DateTime, nullable=True)
    user = relationship("User")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, is_read={self.is_read})>"


class NotificationSettings(BaseModel):
    __tablename__ = "notification_settings"

    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    email_enabled = Column(Boolean, default=True)

    push_enabled = Column(Boolean, default=True)

    user = relationship("User")

    def __repr__(self):
        return f"<NotificationSettings(user_id={self.user_id}, email_enabled={self.email_enabled}, push_enabled={self.push_enabled})>"
