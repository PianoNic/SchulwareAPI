# Push Notifications Setup Guide

## Quick Start

Your SchulwareAPI now supports sending push notifications to iOS and Android Flutter apps **without needing a Firebase backend**!

## What Was Implemented

### Backend (Python/FastAPI)
1. **Database Model**: `Device` model to store registered devices
2. **Push Services**:
   - `APNsClient` - Send to iOS via Apple's servers
   - `FCMClient` - Send to Android via Google's servers (no Firebase project needed!)
   - `NtfyClient` - Send to Android without Google (privacy-focused)
3. **API Endpoints**:
   - `POST /api/device/register` - Register device for notifications
   - `GET /api/device/devices` - List user's devices
   - `DELETE /api/device/devices/{id}` - Unregister device
   - `POST /api/notification/send` - Send test notification

### Files Created
- [src/domain/device.py](src/domain/device.py) - Device database model
- [src/application/services/push_notification_service.py](src/application/services/push_notification_service.py) - Core notification logic
- [src/api/controllers/device_controller.py](src/api/controllers/device_controller.py) - Device registration endpoints
- [src/api/controllers/notification_controller.py](src/api/controllers/notification_controller.py) - Notification sending endpoints
- [FLUTTER_INTEGRATION.md](FLUTTER_INTEGRATION.md) - Complete Flutter integration guide

## Backend Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The updated `requirements.txt` now includes `pyjwt[crypto]` for APNs JWT token generation.

### 2. Run Database Migration

The `Device` table will be created automatically on next startup:

```bash
python asgi.py
```

### 3. Configure Push Credentials

Copy `.env.example` to `.env` (if not already done) and add your push notification credentials:

#### For iOS (Required if you have iOS app):

```bash
# Get these from Apple Developer Console
APNS_KEY_ID=ABC1234567
APNS_TEAM_ID=XYZ9876543
APNS_KEY_PATH=/path/to/AuthKey_ABC1234567.p8
APNS_TOPIC=com.yourcompany.schulware  # Your app's bundle ID
APNS_USE_SANDBOX=true  # Use 'false' for production
```

**How to get APNs credentials:**
1. Go to https://developer.apple.com/account/resources/authkeys/list
2. Click "+" to create a new key
3. Enable "Apple Push Notifications service (APNs)"
4. Download the `.p8` file
5. Note the Key ID and your Team ID

#### For Android (Optional - free!):

```bash
# Get from Google Cloud Console (NOT Firebase Console!)
FCM_SERVER_KEY=AAAAxxxxx:APA91bHxxxxxxxxxxxxxxx
```

**How to get FCM Server Key:**
1. Go to https://console.cloud.google.com
2. Create or select a project
3. Enable "Firebase Cloud Messaging API"
4. Go to APIs & Services → Credentials
5. Create API Key (Server key)

**Note:** You do NOT need a Firebase project! Just the FCM API enabled.

#### For Self-Hosted (Optional):

```bash
# For privacy-focused Android users without Google Services
NTFY_SERVER_URL=https://ntfy.sh  # Use public server or self-host
# NTFY_AUTH_TOKEN=your_token  # Optional, for authenticated server
```

### 4. Test the Setup

Start your API:

```bash
python asgi.py
```

Visit Swagger UI at http://localhost:8000/ and look for:
- **Device** endpoints - for device registration
- **Notification** endpoints - for sending notifications

## Sending Notifications from Your Code

### Example: Send notification when new grade is available

```python
from src.application.services.push_notification_service import push_service

async def notify_new_grade(user_id: int, grade_data: dict):
    """Send push notification when user gets a new grade"""
    await push_service.send_to_user(
        user_id=user_id,
        notification={
            "title": "New Grade Available",
            "body": f"You received a new grade in {grade_data['subject']}",
            "data": {
                "type": "new_grade",
                "grade_id": grade_data["id"],
                "subject": grade_data["subject"]
            }
        }
    )
```

### Example: Send notification to all users

```python
async def notify_system_maintenance():
    """Send maintenance notification to all users"""
    results = await push_service.send_to_all_users(
        notification={
            "title": "Scheduled Maintenance",
            "body": "System will be down for maintenance tonight at 10 PM",
        }
    )
    print(f"Sent to {results['sent']} devices, {results['failed']} failed")
```

## Flutter Integration

See [FLUTTER_INTEGRATION.md](FLUTTER_INTEGRATION.md) for complete Flutter app integration guide.

**Quick summary for Flutter:**
1. Add `push: ^1.0.0` and `unifiedpush: ^5.0.1` to pubspec.yaml
2. Request notification permissions
3. Get device token (APNs/FCM) or endpoint (ntfy)
4. Send to `/api/device/register` endpoint
5. Receive notifications in your app!

## Cost Breakdown

| Platform | Service | Cost |
|----------|---------|------|
| iOS | APNs (Apple Push) | FREE (requires $99/year Apple Developer account for App Store) |
| Android | FCM (Google) | FREE (unlimited) |
| Android | ntfy (self-hosted) | FREE (your server costs) |
| Backend | Your FastAPI | Your hosting costs |

**Total extra cost: $0** ✅

No Firebase subscription, no per-message fees!

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Flutter App                        │
│  iOS (APNs token) | Android GMS (FCM token) | Android (ntfy)│
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                    POST /api/device/register
                             │
┌────────────────────────────┴────────────────────────────────┐
│                   Your SchulwareAPI (FastAPI)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ APNsClient   │  │  FCMClient   │  │ NtfyClient   │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
    Apple's APNs      Google's FCM      Your ntfy Server
  (api.push.apple.com) (fcm.googleapis.com) (self-hosted)
          │                  │                  │
          ▼                  ▼                  ▼
    iOS Devices       Android (GMS)     Android (no GMS)
```

## Next Steps

1. **Configure credentials** in `.env` file
2. **Test with Swagger UI** - use `/api/notification/send` to send test notifications
3. **Integrate with Flutter** - follow [FLUTTER_INTEGRATION.md](FLUTTER_INTEGRATION.md)
4. **Add notification triggers** - integrate with your existing Schulnetz data fetching

## Example Integration: Notify on New Schulnetz Data

You can add notification sending to your existing mobile proxy controller:

```python
# In src/api/controllers/mobile_proxy_controller.py

from src.application.services.push_notification_service import push_service

@router.get("grades", dependencies=[Depends(security)], response_model=List[GradeDto])
async def get_mobile_grades(token: str = Depends(get_current_token)):
    grades = await proxy_mobile_rest_query_async(token, "me/grades", "GET")

    # Optional: Check if there are new grades and notify
    # (You'd need to implement logic to track "new" grades)

    return grades
```

## Troubleshooting

### "APNs credentials not configured" error
- Check that all APNS_* variables are set in `.env`
- Verify the .p8 file path is correct and file exists

### "FCM_SERVER_KEY not configured" error
- Add FCM_SERVER_KEY to `.env`
- Get it from Google Cloud Console (not Firebase Console)

### Notifications not arriving
- Check logs: `tail -f logs/app.log`
- Verify device is registered: `GET /api/device/devices`
- Send test notification: `POST /api/notification/send`
- For iOS: Use sandbox mode for development builds

## Security Notes

- Device tokens are stored securely in your database
- All API endpoints require JWT authentication
- Notifications are only sent to authenticated user's devices
- No device tokens are ever exposed to clients

## Support

For Flutter integration questions, see [FLUTTER_INTEGRATION.md](FLUTTER_INTEGRATION.md).

For backend questions, check the implementation files or API documentation at http://localhost:8000/
