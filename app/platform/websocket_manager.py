"""
WebSocket Connection Manager

Manages WebSocket connections for real-time notifications.
Tracks active connections per user and provides methods to send messages.
"""

from typing import Dict, List

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.platform.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.

    Tracks multiple connections per user (supporting multiple devices/tabs).
    Provides methods to send messages to specific users or broadcast to all.
    """

    def __init__(self):
        # Maps user_id -> list of WebSocket connections
        # A user can have multiple connections (different devices/browser tabs)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Register a new WebSocket connection for a user.

        Args:
            websocket: The WebSocket connection object
            user_id: The authenticated user's ID
        """
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """
        Remove a WebSocket connection for a user.

        Args:
            websocket: The WebSocket connection object to remove
            user_id: The user's ID
        """
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                logger.info(
                    f"User {user_id} disconnected. Remaining connections: {len(self.active_connections[user_id])}"
                )

            # Clean up empty lists
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                logger.info(f"User {user_id} has no more active connections")

    async def send_personal_message(self, message: dict, user_id: str):
        """
        Send a message to all of a specific user's connected devices.

        Args:
            message: The message dictionary to send (will be JSON serialized)
            user_id: The target user's ID

        Returns:
            Number of successful deliveries
        """
        if user_id not in self.active_connections:
            logger.debug(f"User {user_id} is not connected. Message not delivered.")
            return 0

        connections = self.active_connections[user_id]
        successful_sends = 0
        failed_connections = []

        for connection in connections:
            try:
                # Check if connection is still open
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
                    successful_sends += 1
                else:
                    failed_connections.append(connection)
            except Exception as e:
                logger.warning(f"Failed to send message to user {user_id}: {e}")
                failed_connections.append(connection)

        # Clean up failed connections
        for failed_connection in failed_connections:
            await self.disconnect(failed_connection, user_id)

        logger.info(
            f"Sent message to user {user_id}. Successful: {successful_sends}, Failed: {len(failed_connections)}"
        )
        return successful_sends

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected users.

        Args:
            message: The message dictionary to send (will be JSON serialized)

        Returns:
            Number of successful deliveries
        """
        total_sent = 0
        for user_id in list(self.active_connections.keys()):
            sent = await self.send_personal_message(message, user_id)
            total_sent += sent

        logger.info(f"Broadcast message to {total_sent} connections")
        return total_sent

    def get_active_user_count(self) -> int:
        """Get the number of users with at least one active connection."""
        return len(self.active_connections)

    def get_total_connection_count(self) -> int:
        """Get the total number of active WebSocket connections."""
        return sum(len(connections) for connections in self.active_connections.values())


# Global singleton instance
manager = ConnectionManager()
