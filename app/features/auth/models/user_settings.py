import enum
from sqlalchemy import Column, Enum, ForeignKey, String
from app.platform.db.base import BaseModel

class EmailReportPreference(str, enum.Enum):
    none = "none"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"

class UserSettings(BaseModel):
    __tablename__ = "user_settings"

    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    email_report_preference = Column(
        Enum(EmailReportPreference),
        nullable=False,
        default=EmailReportPreference.none,
    )

    def __repr__(self):
        return (
            f"<UserSettings(user_id={self.user_id}, "
            f"email_report_preference={self.email_report_preference})>"
        )
