# Flutter Push Notification Integration Guide

This guide shows how to integrate push notifications with your Flutter app connecting to SchulwareAPI.

## Overview

The integration supports:
- ✅ **iOS** via Apple Push Notification service (APNs)
- ✅ **Android with Google Services** via Firebase Cloud Messaging (FCM)
- ✅ **Android without Google Services** via self-hosted ntfy (UnifiedPush)

## Cost Summary
- **iOS**: $99/year Apple Developer (required for App Store) + FREE APNs
- **Android**: COMPLETELY FREE
- **No per-message fees**

---

## 1. Flutter Dependencies

Add to your `pubspec.yaml`:

```yaml
dependencies:
  # Cross-platform push notifications (no Firebase backend needed!)
  push: ^1.0.0

  # For Android without Google Services (privacy-focused users)
  unifiedpush: ^5.0.1

  # Display notifications in app
  flutter_local_notifications: ^17.0.0

  # HTTP client for your API
  http: ^1.2.0
```

Run:
```bash
flutter pub get
```

---

## 2. Platform Setup

### iOS Setup

#### 2.1. Enable Push Notifications in Xcode
1. Open `ios/Runner.xcworkspace` in Xcode
2. Select your project → Target → Signing & Capabilities
3. Click "+ Capability" → Push Notifications
4. Click "+ Capability" → Background Modes
5. Check "Remote notifications"

#### 2.2. Get APNs Key from Apple Developer
1. Go to https://developer.apple.com/account/resources/authkeys/list
2. Create a new key with "Apple Push Notifications service (APNs)" enabled
3. Download the `.p8` file (e.g., `AuthKey_XXXXXXXXXX.p8`)
4. Note your **Key ID** and **Team ID**

#### 2.3. Update your Backend `.env`
```bash
APNS_KEY_ID=your_key_id_here
APNS_TEAM_ID=your_team_id_here
APNS_KEY_PATH=/path/to/AuthKey_XXXXXXXXXX.p8
APNS_TOPIC=com.yourcompany.schulware  # Your app bundle ID
APNS_USE_SANDBOX=true  # false for production
```

### Android Setup

#### 2.4. Option A: With Google Services (FCM)

1. **Get FCM Server Key** (No Firebase project needed!)
   - Go to Google Cloud Console: https://console.cloud.google.com
   - Create a new project or use existing
   - Enable "Firebase Cloud Messaging API"
   - Go to APIs & Services → Credentials
   - Create API Key (Server key)

2. **Update your Backend `.env`:**
```bash
FCM_SERVER_KEY=your_fcm_server_key_here
```

3. **Add google-services.json** (optional, can skip if you don't need Firebase)
   - If you want to use FCM without Firebase, you can configure it manually
   - The `push` package handles token generation

#### 2.5. Option B: Without Google Services (ntfy/UnifiedPush)

1. **Deploy ntfy server** (see Docker section below)

2. **Update your Backend `.env`:**
```bash
NTFY_SERVER_URL=https://your-ntfy-server.com
```

3. **No additional setup needed** - UnifiedPush handles everything

---

## 3. Flutter Code Implementation

### 3.1. Create Notification Service

Create `lib/services/notification_service.dart`:

```dart
import 'dart:io';
import 'package:push/push.dart';
import 'package:unifiedpush/unifiedpush.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  String? _deviceToken;
  String? _ntfyEndpoint;
  bool _initialized = false;

  /// Initialize push notifications
  Future<void> initialize(String apiBaseUrl, String authToken) async {
    if (_initialized) return;

    // Initialize local notifications
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _localNotifications.initialize(
      settings,
      onDidReceiveNotificationResponse: _onNotificationTapped,
    );

    // Platform-specific initialization
    if (Platform.isIOS) {
      await _initializeIOS(apiBaseUrl, authToken);
    } else if (Platform.isAndroid) {
      await _initializeAndroid(apiBaseUrl, authToken);
    }

    _initialized = true;
  }

  /// Initialize iOS (APNs)
  Future<void> _initializeIOS(String apiBaseUrl, String authToken) async {
    // Request permission
    await Push.instance.requestPermission();

    // Listen for token changes
    Push.instance.token.addListener(() async {
      final token = Push.instance.token.value;
      if (token != null && token != _deviceToken) {
        _deviceToken = token;
        await _registerDevice(
          apiBaseUrl: apiBaseUrl,
          authToken: authToken,
          platform: 'ios',
          pushToken: token,
        );
      }
    });

    // Listen for incoming notifications
    Push.instance.onMessage.listen((message) {
      _showLocalNotification(
        title: message.notification?.title ?? 'Notification',
        body: message.notification?.body ?? '',
      );
    });

    // Listen for notification taps
    Push.instance.onNotificationTap.listen((data) {
      print('Notification tapped: $data');
      // Handle navigation here
    });
  }

  /// Initialize Android
  Future<void> _initializeAndroid(String apiBaseUrl, String authToken) async {
    final hasGoogleServices = await _hasGoogleServices();

    if (hasGoogleServices) {
      // Use FCM
      await _initializeWithFCM(apiBaseUrl, authToken);
    } else {
      // Use UnifiedPush/ntfy
      await _initializeWithUnifiedPush(apiBaseUrl, authToken);
    }
  }

  /// Initialize with FCM (Android with Google)
  Future<void> _initializeWithFCM(String apiBaseUrl, String authToken) async {
    await Push.instance.requestPermission();

    Push.instance.token.addListener(() async {
      final token = Push.instance.token.value;
      if (token != null && token != _deviceToken) {
        _deviceToken = token;
        await _registerDevice(
          apiBaseUrl: apiBaseUrl,
          authToken: authToken,
          platform: 'android',
          hasGms: true,
          pushToken: token,
        );
      }
    });

    Push.instance.onMessage.listen((message) {
      _showLocalNotification(
        title: message.notification?.title ?? 'Notification',
        body: message.notification?.body ?? '',
      );
    });

    Push.instance.onNotificationTap.listen((data) {
      print('Notification tapped: $data');
    });
  }

  /// Initialize with UnifiedPush (Android without Google)
  Future<void> _initializeWithUnifiedPush(
      String apiBaseUrl, String authToken) async {
    await UnifiedPush.initialize(
      onNewEndpoint: (endpoint, instance) async {
        print('UnifiedPush endpoint: $endpoint');
        _ntfyEndpoint = endpoint;

        await _registerDevice(
          apiBaseUrl: apiBaseUrl,
          authToken: authToken,
          platform: 'android',
          hasGms: false,
          ntfyEndpoint: endpoint,
        );
      },
      onMessage: (message, instance) {
        print('UnifiedPush message: $message');

        // Parse message (format varies by distributor)
        final decoded = utf8.decode(message);
        _showLocalNotification(
          title: 'New Notification',
          body: decoded,
        );
      },
      onUnregistered: (instance) {
        print('UnifiedPush unregistered');
        _ntfyEndpoint = null;
      },
    );

    await UnifiedPush.registerApp();
  }

  /// Register device with SchulwareAPI
  Future<void> _registerDevice({
    required String apiBaseUrl,
    required String authToken,
    required String platform,
    bool hasGms = true,
    String? pushToken,
    String? ntfyEndpoint,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$apiBaseUrl/api/device/register'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode({
          'platform': platform,
          'has_gms': hasGms,
          'push_token': pushToken,
          'ntfy_endpoint': ntfyEndpoint,
          'device_name': await _getDeviceName(),
        }),
      );

      if (response.statusCode == 200) {
        print('Device registered successfully');
        final data = jsonDecode(response.body);
        print('Device ID: ${data['device_id']}');
        if (data['ntfy_topic'] != null) {
          print('ntfy topic: ${data['ntfy_topic']}');
        }
      } else {
        print('Failed to register device: ${response.statusCode}');
        print('Response: ${response.body}');
      }
    } catch (e) {
      print('Error registering device: $e');
    }
  }

  /// Show local notification
  Future<void> _showLocalNotification({
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

  /// Handle notification tap
  void _onNotificationTapped(NotificationResponse response) {
    print('Notification tapped: ${response.payload}');
    // Handle navigation here
  }

  /// Check if device has Google Mobile Services
  Future<bool> _hasGoogleServices() async {
    // You can use a package like gms_check or manually check
    // For now, assume true (most devices have GMS)
    return true;
  }

  /// Get device name
  Future<String> _getDeviceName() async {
    // You can use device_info_plus package
    if (Platform.isIOS) {
      return 'iOS Device';
    } else {
      return 'Android Device';
    }
  }

  /// Send test notification to yourself
  Future<void> sendTestNotification(String apiBaseUrl, String authToken) async {
    try {
      final response = await http.post(
        Uri.parse('$apiBaseUrl/api/notification/send'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode({
          'title': 'Test Notification',
          'body': 'This is a test push notification from Schulware!',
          'data': {'test': true},
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        print('Test notification sent: ${data['sent']} devices');
      } else {
        print('Failed to send test notification: ${response.statusCode}');
      }
    } catch (e) {
      print('Error sending test notification: $e');
    }
  }
}
```

### 3.2. Initialize in main.dart

```dart
import 'package:flutter/material.dart';
import 'services/notification_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  runApp(MyApp());
}

class MyApp extends StatefulWidget {
  @override
  _MyAppState createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  final notificationService = NotificationService();

  @override
  void initState() {
    super.initState();
    _initNotifications();
  }

  Future<void> _initNotifications() async {
    // Initialize after user logs in and you have auth token
    const apiBaseUrl = 'https://your-api.com';
    const authToken = 'your-jwt-token-here';

    await notificationService.initialize(apiBaseUrl, authToken);
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

### 3.3. Test Notification Button

```dart
ElevatedButton(
  onPressed: () async {
    await NotificationService().sendTestNotification(
      'https://your-api.com',
      yourAuthToken,
    );
  },
  child: Text('Send Test Notification'),
)
```

---

## 4. Backend Setup

### 4.1. Install Dependencies

```bash
cd SchulwareAPI
pip install -r requirements.txt
```

### 4.2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# iOS
APNS_KEY_ID=your_key_id
APNS_TEAM_ID=your_team_id
APNS_KEY_PATH=/path/to/AuthKey_XXX.p8
APNS_TOPIC=com.yourcompany.schulware
APNS_USE_SANDBOX=true

# Android
FCM_SERVER_KEY=your_fcm_key

# ntfy (optional)
NTFY_SERVER_URL=https://your-ntfy.com
```

### 4.3. Run Backend

```bash
python asgi.py
```

### 4.4. Optional: Deploy ntfy with Docker

Create `docker-compose.yml` in your project root:

```yaml
version: '3'

services:
  ntfy:
    image: binwiederhier/ntfy
    container_name: ntfy
    command:
      - serve
    ports:
      - "8080:80"
    volumes:
      - ./ntfy-cache:/var/cache/ntfy
      - ./ntfy-etc:/etc/ntfy
    environment:
      - TZ=UTC
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d ntfy
```

---

## 5. API Endpoints

Your app can now use:

### Register Device
```http
POST /api/device/register
Authorization: Bearer <token>
Content-Type: application/json

{
  "platform": "ios",
  "push_token": "device_token_here",
  "device_name": "iPhone 14"
}
```

### Get Registered Devices
```http
GET /api/device/devices
Authorization: Bearer <token>
```

### Unregister Device
```http
DELETE /api/device/devices/{device_id}
Authorization: Bearer <token>
```

### Send Test Notification
```http
POST /api/notification/send
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Test",
  "body": "This is a test notification",
  "data": {"key": "value"}
}
```

---

## 6. Sending Notifications from Your Backend

In your Python backend, send notifications like this:

```python
from src.application.services.push_notification_service import push_service

# Send to specific user
await push_service.send_to_user(
    user_id=123,
    notification={
        "title": "New Grade Available",
        "body": "You have a new grade in Mathematics",
        "data": {"grade_id": 456, "subject": "math"}
    }
)

# Send to all users
await push_service.send_to_all_users(
    notification={
        "title": "System Maintenance",
        "body": "Scheduled maintenance tonight at 10 PM"
    }
)
```

---

## 7. Testing

1. **Test on iOS Simulator** (limited - can't receive real push)
   - Use test notification endpoint
   - Local notifications will work

2. **Test on Real iOS Device**
   - Must have valid provisioning profile
   - Sandbox APNs works with development builds
   - Production APNs requires App Store/TestFlight build

3. **Test on Android Emulator**
   - FCM works if Google Play Services installed
   - ntfy works without GMS

4. **Test on Real Android Device**
   - Both FCM and ntfy work perfectly

---

## 8. Production Checklist

- [ ] iOS: Set `APNS_USE_SANDBOX=false` for production
- [ ] iOS: Upload app to App Store with valid provisioning
- [ ] Android: Get production FCM key
- [ ] Deploy ntfy server with HTTPS
- [ ] Test on real devices before release
- [ ] Monitor error logs in GlitchTip/Sentry

---

## Troubleshooting

### iOS not receiving notifications
- Check APNS_TOPIC matches your bundle ID
- Verify .p8 key is valid
- Use sandbox mode for development builds
- Check device token is sent to server

### Android FCM not working
- Verify FCM_SERVER_KEY is correct
- Check device has Google Play Services
- Ensure app has notification permission

### ntfy not working
- Check NTFY_SERVER_URL is accessible
- Verify ntfy endpoint is registered
- Test ntfy server with curl

---

## Cost Summary

**Total cost for unlimited push notifications:**
- iOS: $99/year (Apple Developer Program)
- Android: $0 (FCM is free)
- Server: Your existing hosting costs

No per-message fees, no Firebase subscription needed! 🎉
