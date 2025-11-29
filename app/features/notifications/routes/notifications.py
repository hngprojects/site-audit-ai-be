from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.user import User
from app.features.auth.routes.auth import get_current_user
from app.features.notifications.schemas.notifications import (
    MarkAsReadRequest,
    NotificationListResponse,
    NotificationResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from app.features.notifications.services.notifications import NotificationService
from app.platform.db.session import get_db
from app.platform.response import api_response

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user notifications with pagination."""
    service = NotificationService(db)
    notifications, total, unread_count = await service.get_user_notifications(
        user_id=str(current_user.id),
        skip=skip,
        limit=limit,
        unread_only=unread_only,
    )

    notification_responses = [
        NotificationResponse.model_validate(notification) for notification in notifications
    ]

    return api_response(
        status_code=status.HTTP_200_OK,
        data={
            "notifications": NotificationListResponse(
                notifications=notification_responses,
                total=total,
                unread_count=unread_count,
            ),
        },
    )


@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications."""
    service = NotificationService(db)
    _, _, unread_count = await service.get_user_notifications(
        user_id=str(current_user.id),
        skip=0,
        limit=1,
    )

    return api_response(data={"unread_count": unread_count})


@router.patch("/mark-as-read", response_model=dict)
async def mark_notifications_as_read(
    request: MarkAsReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark specific notifications as read."""
    service = NotificationService(db)
    updated_count = await service.mark_as_read(
        user_id=str(current_user.id),
        notification_ids=request.notification_ids,
    )

    return api_response(data={"updated_count": updated_count})


@router.patch("/mark-all-as-read", response_model=dict)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all user notifications as read."""
    service = NotificationService(db)
    updated_count = await service.mark_all_as_read(user_id=str(current_user.id))

    return api_response(data={"updated_count": updated_count})


@router.delete("/{notification_id}", response_model=dict)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific notification."""
    service = NotificationService(db)
    deleted = await service.delete_notification(
        user_id=str(current_user.id),
        notification_id=notification_id,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")

    return api_response(message="Notification deleted successfully")


@router.delete("", response_model=dict)
async def delete_all_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all user notifications."""
    service = NotificationService(db)
    deleted_count = await service.delete_all_notifications(user_id=str(current_user.id))

    return api_response(data={"deleted_count": deleted_count}, status_code=status.HTTP_200_OK)


@router.get("/settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user notification settings. Creates default settings if they don't exist."""
    service = NotificationService(db)
    settings = await service.get_user_settings(user_id=str(current_user.id))

    return api_response(
        status_code=status.HTTP_200_OK,
        data={"settings": NotificationSettingsResponse.model_validate(settings)},
    )


@router.patch("/settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user notification settings."""
    service = NotificationService(db)
    settings = await service.create_or_update_settings(
        user_id=str(current_user.id),
        settings_data=settings_update.model_dump(exclude_unset=True),
    )

    return api_response(
        status_code=status.HTTP_200_OK,
        data={"settings": NotificationSettingsResponse.model_validate(settings)},
    )


@router.post("/test", response_model=NotificationResponse)
async def send_test_notification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test notification to the current user."""
    service = NotificationService(db)
    from app.features.notifications.models.notifications import NotificationType

    notification = await service.create_notification(
        user_id=str(current_user.id),
        title="Test Notification",
        message="This is a test notification from Site Audit AI.",
        notification_type=NotificationType.SYSTEM_ALERT,
        send_email_notification=False,
        send_push_notification=False,
    )

    return api_response(
        status_code=status.HTTP_201_CREATED,
        data={"notification": NotificationResponse.model_validate(notification)},
    )
