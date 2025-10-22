# Push Notifications for Open-Source App (No App Store)

## 🎉 Good News!

Since your app is **open-source and NOT distributed via App Store/Play Store**, you can use **100% self-hosted push notifications** with **ntfy**!

---

## ✅ **Recommended Setup: ntfy Only**

```
Your FastAPI Backend ──► Your ntfy Server ──► Flutter App
     (self-hosted)        (self-hosted)      (sideloaded)
```

**Why this is perfect for you:**
- ✅ **100% self-hosted** (no Apple/Google dependencies)
- ✅ **Completely free** (just your server costs)
- ✅ **Open source** (ntfy is FOSS)
- ✅ **Works in background** (even when app closed!)
- ✅ **No App Store approval needed**
- ✅ **No developer accounts needed** ($0/year)
- ✅ **Privacy-focused** (your users will love this!)
- ✅ **Works great for F-Droid/APK distribution**

---

## 🚀 **Implementation Guide**

### **1. Deploy ntfy Server**

#### Option A: Docker (Recommended)

Create `docker-compose.yml` in your project root:

```yaml
version: '3'

services:
  # Your existing API
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./db:/app/db
      - ./.env:/app/.env
    restart: unless-stopped

  # ntfy server for push notifications
  ntfy:
    image: binwiederhier/ntfy:latest
    container_name: schulware-ntfy
    command:
      - serve
    ports:
      - "8080:80"
    volumes:
      - ./ntfy-cache:/var/cache/ntfy
      - ./ntfy-config:/etc/ntfy
    environment:
      - TZ=UTC
      - NTFY_BASE_URL=https://ntfy.yourdomain.com  # Change to your domain
      - NTFY_UPSTREAM_BASE_URL=https://ntfy.sh
      - NTFY_CACHE_FILE=/var/cache/ntfy/cache.db
      - NTFY_AUTH_FILE=/var/cache/ntfy/auth.db
      - NTFY_AUTH_DEFAULT_ACCESS=deny-all  # Require authentication
      - NTFY_BEHIND_PROXY=true
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "wget -q --tries=1 http://localhost:80/v1/health -O - | grep -Eo '\"healthy\"\\s*:\\s*true' || exit 1"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 40s
```

Start services:
```bash
docker-compose up -d
```

#### Option B: Manual Installation

```bash
# Linux
sudo apt install ntfy
sudo systemctl enable ntfy
sudo systemctl start ntfy

# Or download from GitHub
wget https://github.com/binwiederhier/ntfy/releases/latest/download/ntfy_amd64.deb
sudo dpkg -i ntfy_amd64.deb
```

#### Option C: Use Public ntfy.sh (For Testing)

You can use the free public server `https://ntfy.sh` for testing:
```bash
# In .env
NTFY_SERVER_URL=https://ntfy.sh
```

⚠️ **Warning:** Public server is fine for testing, but self-host for production!

---

### **2. Configure Backend**

Update `.env`:

```bash
# ntfy Configuration
NTFY_SERVER_URL=http://localhost:8080
# Optional: Add authentication (recommended for production)
NTFY_AUTH_TOKEN=your_secret_token_here
```

---

### **3. Simplified Backend (ntfy Only)**

Since you don't need APNs/FCM, let's simplify your implementation:

Update `src/application/services/push_notification_service.py`:

```python
import httpx
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NtfyClient:
    """Client for sending push notifications via self-hosted ntfy server"""

    def __init__(self):
        self.ntfy_server_url = os.getenv("NTFY_SERVER_URL", "http://localhost:8080")
        self.ntfy_auth_token = os.getenv("NTFY_AUTH_TOKEN")

    async def send(self, topic: str, notification: Dict) -> bool:
        """
        Send push notification via ntfy

        Args:
            topic: ntfy topic (user-specific, e.g., "user_123")
            notification: Dict with 'title', 'body', and optional fields

        Returns:
            True if successful, False otherwise
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Title": notification.get("title", "Notification"),
                "Priority": str(notification.get("priority", 3)),  # 1-5
            }

            if self.ntfy_auth_token:
                headers["Authorization"] = f"Bearer {self.ntfy_auth_token}"

            # Add optional fields
            if notification.get("tags"):
                headers["Tags"] = ",".join(notification["tags"])
            if notification.get("click_url"):
                headers["Click"] = notification["click_url"]
            if notification.get("icon_url"):
                headers["Icon"] = notification["icon_url"]

            # Message body
            message = notification.get("body", "")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ntfy_server_url}/{topic}",
                    headers=headers,
                    content=message,
                    timeout=10.0
                )

                if response.status_code == 200:
                    logger.info(f"Successfully sent ntfy notification to topic: {topic}")
                    return True
                else:
                    logger.error(f"ntfy error: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send ntfy notification: {e}")
            return False


class PushNotificationService:
    """Simplified service for ntfy-only push notifications"""

    def __init__(self):
        self.ntfy_client = NtfyClient()

    async def send_to_user(self, user_id: int, notification: Dict) -> Dict[str, int]:
        """
        Send notification to user via ntfy

        Args:
            user_id: User ID
            notification: Notification content

        Returns:
            Dict with results
        """
        # Each user gets their own topic
        topic = f"schulware_user_{user_id}"

        success = await self.ntfy_client.send(topic, notification)

        return {
            "sent": 1 if success else 0,
            "failed": 0 if success else 1,
            "total": 1
        }

    async def send_to_all_users(self, notification: Dict) -> Dict[str, int]:
        """
        Send notification to all users

        Args:
            notification: Notification content

        Returns:
            Aggregate results
        """
        from src.domain.user import User

        users = User.select()
        results = {"sent": 0, "failed": 0, "total": 0}

        for user in users:
            result = await self.send_to_user(user.id, notification)
            results["sent"] += result["sent"]
            results["failed"] += result["failed"]
            results["total"] += result["total"]

        return results


# Singleton instance
push_service = PushNotificationService()
```

**Much simpler!** No APNs/FCM complexity needed.

---

### **4. Simplified Device Model**

Update `src/domain/device.py` (or just remove it - you don't need it!):

Since ntfy uses topics instead of device tokens, you don't actually need to store device info. Each user just subscribes to their topic `schulware_user_{user_id}`.

**You can delete the Device model entirely** if you want to keep it super simple!

---

### **5. Flutter Integration (UnifiedPush)**

#### Add Dependencies

`pubspec.yaml`:

```yaml
dependencies:
  unifiedpush: ^5.0.1
  flutter_local_notifications: ^17.0.0
  http: ^1.2.0
```

#### Simple Implementation

`lib/services/ntfy_notification_service.dart`:

```dart
import 'dart:convert';
import 'package:unifiedpush/unifiedpush.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NtfyNotificationService {
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  String? _endpoint;
  bool _initialized = false;

  Future<void> initialize(String apiBaseUrl, int userId) async {
    if (_initialized) return;

    // Initialize local notifications
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _localNotifications.initialize(settings);

    // Initialize UnifiedPush
    await UnifiedPush.initialize(
      onNewEndpoint: (endpoint, instance) async {
        print('ntfy endpoint: $endpoint');
        _endpoint = endpoint;

        // No need to register with backend - just subscribe to your topic!
        // The topic is: schulware_user_{userId}
      },
      onMessage: (message, instance) async {
        print('Received notification: $message');

        // Parse the notification
        final decoded = utf8.decode(message);

        try {
          final data = jsonDecode(decoded);
          await _showNotification(
            title: data['title'] ?? 'Notification',
            body: data['message'] ?? '',
          );
        } catch (e) {
          // Plain text message
          await _showNotification(
            title: 'Schulware',
            body: decoded,
          );
        }
      },
      onUnregistered: (instance) {
        print('UnifiedPush unregistered');
        _endpoint = null;
      },
    );

    // Register the app
    await UnifiedPush.registerApp();

    // Get available distributors
    final distributors = await UnifiedPush.getDistributors();
    print('Available distributors: $distributors');

    _initialized = true;
  }

  Future<void> _showNotification({
    required String title,
    required String body,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      'schulware_channel',
      'Schulware Notifications',
      channelDescription: 'Notifications from Schulware',
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

  String? get endpoint => _endpoint;
}
```

#### Usage in Your App

```dart
import 'package:flutter/material.dart';
import 'services/ntfy_notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(MyApp());
}

class MyApp extends StatefulWidget {
  @override
  _MyAppState createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final notificationService = NtfyNotificationService();

  @override
  void initState() {
    super.initState();
    _initNotifications();
  }

  Future<void> _initNotifications() async {
    // After user logs in and you have their user ID
    final userId = 123; // Get from your auth

    await notificationService.initialize(
      'http://your-api.com',
      userId,
    );

    print('ntfy endpoint: ${notificationService.endpoint}');
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Schulware',
      home: HomePage(),
    );
  }
}
```

---

### **6. Users Need ntfy Distributor App**

Since you're distributing outside app stores, your users need to install a **UnifiedPush distributor**:

#### Recommended: ntfy App

**Android:**
- F-Droid: https://f-droid.org/packages/io.heckel.ntfy/
- GitHub: https://github.com/binwiederhier/ntfy-android/releases
- Direct APK download available

**iOS:**
- App Store: https://apps.apple.com/app/ntfy/id1625396347
- (Or they can use your self-hosted ntfy web interface)

#### Tell your users:

1. Install ntfy app from F-Droid or GitHub
2. Add your ntfy server URL (if self-hosted)
3. Install your Schulware app
4. Notifications work automatically!

---

## 📝 **Simplified Architecture**

```
┌─────────────────────────────────────────┐
│  Your Schulware Flutter App             │
│  - Uses UnifiedPush package             │
│  - Subscribes to: schulware_user_{id}   │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  ntfy Distributor App (installed by user)│
│  - Maintains connection to ntfy server   │
│  - Wakes up your app with notifications │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│  Your ntfy Server (Docker)              │
│  - Receives from your FastAPI           │
│  - Sends to user devices                │
└───────────────┬─────────────────────────┘
                ▲
                │
┌───────────────┴─────────────────────────┐
│  Your FastAPI Backend                   │
│  push_service.send_to_user(user_id, ...) │
│  → Sends to: schulware_user_{user_id}   │
└─────────────────────────────────────────┘
```

---

## 🎯 **Advantages for Open-Source Apps**

| Feature | Your Setup (ntfy) | Commercial (APNs/FCM) |
|---------|-------------------|----------------------|
| **Cost** | $0 | $99/year (iOS) |
| **Privacy** | ✅ Full control | ❌ Apple/Google track |
| **Self-hosted** | ✅ Yes | ⚠️ Backend only |
| **Open source** | ✅ Yes | ❌ No |
| **Works in China** | ✅ Yes | ❌ FCM blocked |
| **F-Droid compatible** | ✅ Yes | ❌ Needs GMS |
| **No accounts needed** | ✅ Yes | ❌ Developer accounts |
| **Community loves it** | ✅ Yes | ⚠️ Mixed |

---

## 🚀 **Quick Start**

### 1. Start ntfy server:

```bash
docker-compose up -d ntfy
```

### 2. Test it works:

```bash
# Send test notification
curl -d "Hello from Schulware!" http://localhost:8080/schulware_user_123

# Subscribe in browser
# Visit: http://localhost:8080/schulware_user_123
```

### 3. Update your backend:

```python
from src.application.services.push_notification_service import push_service

await push_service.send_to_user(
    user_id=123,
    notification={
        "title": "New Grade",
        "body": "You got an A in Math!",
        "tags": ["school", "grades"],
        "priority": 4
    }
)
```

### 4. Flutter app subscribes automatically when initialized!

---

## 📱 **User Setup Guide**

Include this in your app's README:

```markdown
# Push Notifications Setup

1. Install ntfy from F-Droid: https://f-droid.org/packages/io.heckel.ntfy/
2. Open ntfy app
3. Settings → Add server → Enter: https://ntfy.yourdomain.com
4. Install Schulware app
5. Login to Schulware
6. Notifications work automatically! 🎉

No Google account needed. No tracking. Fully private.
```

---

## 💡 **Pro Tips**

### Use Different Topics

```python
# User-specific
await push_service.send_to_user(123, {...})  # schulware_user_123

# Broadcast to everyone
topic = "schulware_all"
await ntfy_client.send(topic, {...})

# Class-specific
topic = "schulware_class_10a"
await ntfy_client.send(topic, {...})
```

### Add Rich Notifications

```python
await push_service.send_to_user(
    user_id=123,
    notification={
        "title": "📚 New Grade Available",
        "body": "You received an A in Mathematics!",
        "tags": ["tada", "school"],  # Emojis!
        "click_url": "schulware://grades/123",
        "icon_url": "https://yourdomain.com/icon.png",
        "priority": 5  # High priority
    }
)
```

---

## 🎉 **Summary**

For your open-source app distributed outside app stores, **ntfy is perfect**:

- ✅ **100% self-hosted**
- ✅ **$0 cost**
- ✅ **Privacy-focused** (your users will love this!)
- ✅ **Open source** (matches your app's philosophy)
- ✅ **Works great with F-Droid**
- ✅ **No Google/Apple dependencies**
- ✅ **Simple to implement**

This is **the best option** for your use case! 🚀
