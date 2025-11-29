from datetime import datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class ApiRespnse(BaseModel, Generic[T]):
    message: str
    status_code: int
    status: str
    data: Optional[T] = None


class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str


class NotificationCreate(NotificationBase):
    user_id: str


class NotificationResponse(NotificationBase):
    id: str
    user_id: str
    is_read: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    unread_count: int


class MarkAsReadRequest(BaseModel):
    notification_ids: list[str] = Field(..., min_length=1, description="List of notification IDs")


class NotificationSettingsBase(BaseModel):
    email_enabled: bool = True
    push_enabled: bool = True


class NotificationSettingsUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None


class NotificationSettingsResponse(NotificationSettingsBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
