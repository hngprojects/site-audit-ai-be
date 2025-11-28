import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models.notifications import (
    Notification,
    NotificationPriority,
    NotificationSettings,
    NotificationType,
)
from app.features.notifications.services.push_notification import PushNotificationService
from app.platform.logger import get_logger
from app.platform.services.email import send_email

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.push_service = PushNotificationService()

    async def create_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: Optional[NotificationType] = NotificationType.SYSTEM_ALERT,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        action_url: Optional[str] = None,
        meta: Optional[str] = None,
        send_email_notification: bool = True,
        send_push_notification: bool = True,
    ) -> Notification:
        """
        Create a new notification for a user.
        """
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            action_url=action_url,
            meta=json.dumps(meta) if meta else None,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        logger.info(f"Created notification for user {user_id}: {title}")

        settings = await self.get_user_settings(user_id)
        if send_email_notification and bool(settings.email_enabled):
            await self._send_email_notification(user_id, title, message)

        return notification

    async def get_user_settings(self, user_id: str) -> NotificationSettings:
        """
        Get user notification settings. Creates default settings if they don't exist.
        """
        stmt = select(NotificationSettings).where(NotificationSettings.user_id == user_id)
        result = await self.db.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            settings = NotificationSettings(user_id=user_id)
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)

        return settings

    async def create_or_update_settings(
        self, user_id: str, settings_data: dict[str, Any]
    ) -> NotificationSettings:
        """
        Create or update user notification settings.
        """
        settings = await self.get_user_settings(user_id)

        for key, value in settings_data.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    async def _send_email_notification(self, user_id: str, title: str, message: str):
        """Send email notification to user."""
        from app.features.auth.models.user import User

        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.email is not None:
            email_body = f"""
            <h2>{title}</h2>
            <p>{message}</p>
            <p>This is an automated notification from Site Audit AI.</p>
            """
            send_email(str(user.email), title, email_body)

    async def _send_push_notification(self):
        # TODO: push notifications
        """Send push notification to user's devices."""
        await self.push_service.send_notification()
