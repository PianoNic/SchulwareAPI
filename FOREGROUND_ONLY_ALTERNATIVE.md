# Foreground-Only Notifications (100% Self-Hosted Alternative)

## ⚠️ Warning: Limited Functionality

This approach works **ONLY when the app is open**. No notifications when app is closed or in background.

## When to Use This

- Testing/development only
- Internal apps where users keep app open
- Apps with active usage (like chat apps where users are always in the app)

## ❌ When NOT to Use This

- Production apps (users expect background notifications)
- School apps (users won't keep app open all day)
- Any app competing with Firebase/professional apps

---

## Implementation

### Backend: Add WebSocket Endpoint

Create `src/api/controllers/websocket_controller.py`:

```python
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
from src.api.router_registry import SchulwareAPIRouter
from src.application.services.token_service import decode_jwt_token
import logging

logger = logging.getLogger(__name__)

router = SchulwareAPIRouter()

# Store active WebSocket connections
active_connections: Dict[int, Set[WebSocket]] = {}


@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real-time notifications (foreground only)

    Usage: ws://localhost:8000/api/websocket/notifications?token=your_jwt_token
    """
    await websocket.accept()

    user_id = None
    try:
        # Authenticate
        payload = decode_jwt_token(token)
        user_email = payload.get("sub")

        # Get user ID (you'll need to fetch from DB)
        from src.domain.user import User
        user = User.get_or_none(User.email == user_email)
        if not user:
            await websocket.close(code=1008, reason="User not found")
            return

        user_id = user.id

        # Register connection
        if user_id not in active_connections:
            active_connections[user_id] = set()
        active_connections[user_id].add(websocket)

        logger.info(f"WebSocket connected for user {user_id}")

        # Keep connection alive
        while True:
            # Wait for messages (ping/pong)
            data = await websocket.receive_text()

            # Echo back (optional)
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        if user_id and user_id in active_connections:
            active_connections[user_id].discard(websocket)
            if not active_connections[user_id]:
                del active_connections[user_id]


async def send_websocket_notification(user_id: int, notification: dict):
    """
    Send notification via WebSocket to user's active connections

    Args:
        user_id: User ID to send to
        notification: Notification data
    """
    if user_id not in active_connections:
        logger.debug(f"No active WebSocket for user {user_id}")
        return

    import json
    message = json.dumps(notification)

    # Send to all active connections for this user
    disconnected = set()
    for websocket in active_connections[user_id]:
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            disconnected.add(websocket)

    # Remove disconnected sockets
    for ws in disconnected:
        active_connections[user_id].discard(ws)
```

Update `src/application/services/push_notification_service.py`:

```python
# Add at the top
from src.api.controllers.websocket_controller import send_websocket_notification

# Add to PushNotificationService.send_to_user():
async def send_to_user(self, user_id: int, notification: Dict) -> Dict[str, int]:
    """Send notification to all registered devices for a user"""

    # ... existing code ...

    # ALSO send via WebSocket if connected
    try:
        await send_websocket_notification(user_id, notification)
    except Exception as e:
        logger.error(f"Failed to send WebSocket notification: {e}")

    return results
```

---

### Flutter: WebSocket Client

Add to `pubspec.yaml`:

```yaml
dependencies:
  web_socket_channel: ^2.4.0
```

Create `lib/services/websocket_notification_service.dart`:

```dart
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class WebSocketNotificationService {
  WebSocketChannel? _channel;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  Future<void> connect(String apiUrl, String authToken) async {
    // Initialize local notifications
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );
    await _localNotifications.initialize(settings);

    // Connect to WebSocket
    final wsUrl = apiUrl.replaceFirst('http', 'ws');
    _channel = WebSocketChannel.connect(
      Uri.parse('$wsUrl/api/websocket/notifications?token=$authToken'),
    );

    // Listen for messages
    _channel!.stream.listen(
      (message) {
        print('Received notification: $message');

        final data = jsonDecode(message);
        _showNotification(
          title: data['title'] ?? 'Notification',
          body: data['body'] ?? '',
        );
      },
      onError: (error) {
        print('WebSocket error: $error');
      },
      onDone: () {
        print('WebSocket closed');
        _reconnect(apiUrl, authToken);
      },
    );

    // Send ping every 30 seconds to keep alive
    _startPingTimer();
  }

  void _startPingTimer() {
    Timer.periodic(Duration(seconds: 30), (timer) {
      if (_channel != null) {
        _channel!.sink.add('ping');
      } else {
        timer.cancel();
      }
    });
  }

  Future<void> _reconnect(String apiUrl, String authToken) async {
    await Future.delayed(Duration(seconds: 5));
    await connect(apiUrl, authToken);
  }

  Future<void> _showNotification({
    required String title,
    required String body,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      'websocket_channel',
      'WebSocket Notifications',
      importance: Importance.high,
      priority: Priority.high,
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _localNotifications.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      details,
    );
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
  }
}
```

Usage in Flutter:

```dart
// In your main app
final wsService = WebSocketNotificationService();

await wsService.connect(
  'http://your-api.com',
  yourAuthToken,
);

// Disconnect when app closes
@override
void dispose() {
  wsService.disconnect();
  super.dispose();
}
```

---

## Comparison

| Feature | Platform Push (APNs/FCM) | WebSocket (100% Self-Hosted) |
|---------|-------------------------|------------------------------|
| **Background notifications** | ✅ Yes | ❌ No |
| **App closed notifications** | ✅ Yes | ❌ No |
| **Battery efficient** | ✅ Yes | ❌ No (terrible) |
| **Reliable** | ✅ Yes | ⚠️ Drops often |
| **Production ready** | ✅ Yes | ❌ No |
| **User experience** | ✅ Excellent | ❌ Poor |
| **Self-hosted** | ⚠️ Backend only | ✅ Fully |
| **Cost** | ✅ Free | ✅ Free |

---

## Recommendation

**DON'T use WebSocket-only approach for production.**

Instead, use the **hybrid approach** I implemented:
- Your backend is self-hosted ✅
- You control all logic ✅
- You just use Apple/Google as delivery services (like postal service) ✅
- Zero extra cost ✅
- Professional user experience ✅

---

## Why This Matters

**Think of it like email:**
- You control your email server (backend)
- You decide what to send and when
- But you still need SMTP to deliver to Gmail/Outlook users
- That's exactly what APNs/FCM are - delivery services

**Your implementation:**
- ✅ Your FastAPI backend = Your email server
- ✅ You control all logic
- ✅ APNs/FCM = SMTP (just delivery)
- ✅ No Firebase dependency
- ✅ Fully self-hosted backend
