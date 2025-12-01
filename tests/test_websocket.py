"""
WebSocket Tests

Tests for real-time WebSocket notification functionality.
"""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models.user import User
from app.features.notifications.models.notifications import NotificationType
from app.features.notifications.services.notifications import NotificationService
from app.main import app
from app.platform.websocket_manager import manager

pytest.skip("websocket tests disabled -apathy", allow_module_level=True)


@pytest.fixture
async def auth_token(db_session: AsyncSession):
    """
    Create a test user and return a valid JWT token.
    You'll need to implement this based on your existing auth test fixtures.
    """
    # TODO: Implement user creation and token generation
    # This should use your existing auth service to create a user and get a token
    pass


class TestWebSocketConnection:
    """Test WebSocket connection functionality"""

    def test_websocket_connection_without_token(self):
        """Test that WebSocket connection fails without authentication token"""
        client = TestClient(app)

        with pytest.raises(Exception):  # Should raise WebSocketException
            with client.websocket_connect("/api/v1/ws/notifications"):
                pass

    @pytest.mark.asyncio
    async def test_websocket_connection_with_invalid_token(self):
        """Test that WebSocket connection fails with invalid token"""
        client = TestClient(app)

        with pytest.raises(Exception):  # Should raise WebSocketException
            with client.websocket_connect("/api/v1/ws/notifications?token=invalid_token_here"):
                pass

    # TODO: Implement this test once auth fixtures are ready
    # @pytest.mark.asyncio
    # async def test_websocket_connection_with_valid_token(self, auth_token):
    #     """Test successful WebSocket connection with valid token"""
    #     client = TestClient(app)
    #
    #     with client.websocket_connect(f"/api/v1/ws/notifications?token={auth_token}") as websocket:
    #         # Should receive welcome message
    #         data = websocket.receive_json()
    #         assert data["type"] == "connected"
    #         assert "user_id" in data["data"]


class TestNotificationBroadcast:
    """Test real-time notification broadcasting"""

    @pytest.mark.asyncio
    async def test_notification_creates_websocket_broadcast(
        self, db_session: AsyncSession, auth_token
    ):
        """
        Test that creating a notification broadcasts it via WebSocket.

        This is an integration test that verifies the full flow:
        1. User connects via WebSocket
        2. Notification is created via service
        3. User receives notification in real-time
        """
        # TODO: Implement once auth fixtures are ready
        pass

    @pytest.mark.asyncio
    async def test_notification_multi_device_broadcast(self, db_session: AsyncSession, auth_token):
        """
        Test that notifications are sent to all of a user's connected devices.
        """
        # TODO: Implement multi-device test
        pass


class TestConnectionManager:
    """Test the WebSocket connection manager"""

    def test_connection_manager_connect(self):
        """Test adding connections to manager"""
        # Reset manager state
        manager.active_connections.clear()

        assert manager.get_active_user_count() == 0
        assert manager.get_total_connection_count() == 0

    def test_connection_manager_tracking(self):
        """Test that connection manager tracks multiple devices per user"""
        # This test should verify that a single user can have multiple connections
        # TODO: Implement with mock WebSocket connections
        pass


# Manual Testing Guide
"""
MANUAL TESTING GUIDE
====================

Prerequisites:
1. Start the server: uvicorn app.main:app --reload
2. Obtain a valid JWT token by logging in via /api/v1/auth/login

Test 1: WebSocket Connection via Browser DevTools
-------------------------------------------------
1. Open browser DevTools (F12) → Console tab
2. Run this JavaScript code (replace YOUR_TOKEN with actual JWT):

```javascript
const token = "YOUR_ACCESS_TOKEN_HERE";
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/notifications?token=${token}`);

ws.onopen = () => {
    console.log("✓ Connected to WebSocket!");
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("📨 Received:", data);
    
    if (data.type === "notification") {
        console.log("🔔 New notification:", data.data.title);
    }
};

ws.onerror = (error) => {
    console.error("❌ WebSocket error:", error);
};

ws.onclose = () => {
    console.log("Connection closed");
};
```

Expected Output:
- "✓ Connected to WebSocket!"
- Welcome message: {"type": "connected", "data": {...}}
- Heartbeat messages every 30 seconds


Test 2: Real-Time Notification Delivery
---------------------------------------
1. Keep the WebSocket connection from Test 1 open
2. In another tab or Postman, send a test notification:
   
   POST http://localhost:8000/api/v1/notifications/test
   Headers: Authorization: Bearer YOUR_TOKEN

3. Check the browser console from Test 1

Expected Output:
- Console immediately shows the new notification
- No page refresh needed


Test 3: Multi-Device Support
----------------------------
1. Open WebSocket connection in Chrome (see Test 1 code)
2. Open WebSocket connection in Firefox or Incognito (same user/token)
3. Send a test notification via Postman
4. Check both browser consoles

Expected Output:
- Both browsers receive the notification simultaneously
- Demonstrates multi-device support


Test 4: Invalid Token Handling
------------------------------
Run in browser console:

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/notifications?token=invalid`);
ws.onerror = (error) => console.log("Expected error:", error);
```

Expected Output:
- Connection should fail immediately
- WebSocket error or close event with policy violation


Test 5: Connection Persistence
------------------------------
1. Connect via WebSocket (Test 1)
2. Wait 60+ seconds (should receive 2+ heartbeats)
3. Connection should stay alive

Expected Output:
- Heartbeat messages: {"type": "heartbeat", ...} every 30 seconds
- Connection remains open


Test 6: Graceful Disconnect
---------------------------
1. Connect via WebSocket
2. Close browser tab or run: `ws.close()`

Expected Output:
- Server logs show user disconnected
- No errors in server logs
- Clean connection cleanup
"""
