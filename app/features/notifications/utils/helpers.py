from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notifications.models.notifications import NotificationType
from app.features.notifications.services.notifications import NotificationService


async def notify_user(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    notification_type: Optional[NotificationType] = NotificationType.SYSTEM_ALERT,
    send_email: bool = True,
    send_push: bool = True,
):
    """
    Helper function to create a notification from anywhere.

    Usage example:
        await notify_user(
            db=db,
            user_id=user.id,
            title="Scan Complete",
            message="Your website scan has completed successfully",
            notification_type="scan_complete",
            reference_id=scan.id,
            reference_type="scan",
        )
    """
    service = NotificationService(db)
    return await service.create_notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        send_email_notification=send_email,
        send_push_notification=send_push,
    )
