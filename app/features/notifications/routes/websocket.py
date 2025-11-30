"""
WebSocket Routes for Real-Time Notifications

Provides WebSocket endpoint for clients to receive real-time notification updates.
"""

import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db.session import get_db
from app.platform.logger import get_logger
from app.platform.websocket_auth import authenticate_websocket
from app.platform.websocket_manager import manager

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket Notifications"])


@router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(
    websocket: WebSocket,
    token: str,  # JWT token passed as query parameter
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time notifications.

    Usage:
        ws://localhost:8000/api/v1/ws/notifications?token=<your_jwt_token>

    The client will receive messages in this format:
        {
            "type": "notification",
            "data": {
                "id": "...",
                "title": "...",
                "message": "...",
                "notification_type": "...",
                "priority": "...",
                "created_at": "...",
                "is_read": false,
                "action_url": "..."
            }
        }

    Heartbeat messages are sent every 30 seconds to keep connection alive:
        {"type": "heartbeat", "data": {"timestamp": "..."}}
    """
    user = None
    user_id = None

    try:
        # Authenticate the WebSocket connection
        user = await authenticate_websocket(token, db)
        user_id = str(user.id)

        # Register the connection
        await manager.connect(websocket, user_id)

        logger.info(f"WebSocket connection established for user {user_id}")

        # Send welcome message
        await websocket.send_json(
            {
                "type": "connected",
                "data": {
                    "message": "Successfully connected to notification stream",
                    "user_id": user_id,
                },
            }
        )

        # Keep the connection alive with periodic heartbeats
        while True:
            # Send heartbeat every 30 seconds to keep connection alive
            await asyncio.sleep(30)
            await websocket.send_json(
                {
                    "type": "heartbeat",
                    "data": {"status": "alive"},
                }
            )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # Clean up connection on disconnect
        if user_id:
            await manager.disconnect(websocket, user_id)
            logger.info(f"WebSocket connection cleaned up for user {user_id}")
