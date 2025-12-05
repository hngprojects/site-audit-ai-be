from enum import Enum
from sqlalchemy import Column, String, JSON, Enum as SQLEnum, Text
from uuid_extension import uuid7

from app.platform.db.base import BaseModel


class RequestStatus(str, Enum):
    PENDING = "pending"
    RECEIVED = "received"
    FAILED = "failed"
    COMPLETED = "completed"


class RequestForm(BaseModel):
    __tablename__ = "request_forms"

    request_id = Column(String(50), nullable=False, unique=True, index=True, default=lambda: str(uuid7()))
    # user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # job_id = Column(String, ForeignKey("scan_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(70), nullable=False, index=True)
    job_id = Column(String(70), nullable=False, index=True)
    additional_notes = Column(Text, nullable=True)
    issues = Column(JSON, nullable=True)
    status = Column(SQLEnum(RequestStatus), nullable=False, default=RequestStatus.PENDING)

    def __repr__(self) -> str:
        return (
            f"<RequestForm(request_id='{self.request_id}', user_id='{self.user_id}', "
            f"job_id='{self.job_id}', status='{self.status}')>"
        )
