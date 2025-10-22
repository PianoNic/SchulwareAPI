import httpx
import jwt
import time
import os
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class APNsClient:
    """Client for sending push notifications to iOS via Apple Push Notification service"""

    def __init__(self):
        self.apns_key_id = os.getenv("APNS_KEY_ID")
        self.apns_team_id = os.getenv("APNS_TEAM_ID")
        self.apns_key_path = os.getenv("APNS_KEY_PATH")
        self.apns_topic = os.getenv("APNS_TOPIC")  # Your app bundle ID
        self.apns_use_sandbox = os.getenv("APNS_USE_SANDBOX", "true").lower() == "true"

        self.base_url = "https://api.sandbox.push.apple.com" if self.apns_use_sandbox else "https://api.push.apple.com"

    def _create_jwt_token(self) -> str:
        """Create JWT token for APNs authentication"""
        if not all([self.apns_key_id, self.apns_team_id, self.apns_key_path]):
            raise ValueError("APNs credentials not configured")

        # Read the .p8 key file
        with open(self.apns_key_path, 'r') as f:
            key = f.read()

        # Create JWT token
        headers = {
            "alg": "ES256",
            "kid": self.apns_key_id
        }

        payload = {
            "iss": self.apns_team_id,
            "iat": int(time.time())
        }

        token = jwt.encode(payload, key, algorithm="ES256", headers=headers)
        return token

    async def send(self, device_token: str, notification: Dict) -> bool:
        """
        Send push notification to iOS device

        Args:
            device_token: APNs device token
            notification: Dict with 'title' and 'body' keys

        Returns:
            True if successful, False otherwise
        """
        try:
            auth_token = self._create_jwt_token()

            payload = {
                "aps": {
                    "alert": {
                        "title": notification.get("title", ""),
                        "body": notification.get("body", "")
                    },
                    "sound": "default",
                    "badge": notification.get("badge", 1)
                },
                "data": notification.get("data", {})
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/3/device/{device_token}",
                    headers={
                        "authorization": f"bearer {auth_token}",
                        "apns-topic": self.apns_topic,
                        "apns-push-type": "alert",
                        "apns-priority": "10"
                    },
                    json=payload,
                    timeout=10.0
                )

                if response.status_code == 200:
                    logger.info(f"Successfully sent APNs notification to device")
                    return True
                else:
                    logger.error(f"APNs error: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send APNs notification: {e}")
            return False


class FCMClient:
    """Client for sending push notifications to Android via Firebase Cloud Messaging"""

    def __init__(self):
        self.fcm_server_key = os.getenv("FCM_SERVER_KEY")
        self.fcm_api_url = "https://fcm.googleapis.com/fcm/send"

    async def send(self, device_token: str, notification: Dict) -> bool:
        """
        Send push notification to Android device via FCM

        Args:
            device_token: FCM device token
            notification: Dict with 'title' and 'body' keys

        Returns:
            True if successful, False otherwise
        """
        if not self.fcm_server_key:
            logger.error("FCM_SERVER_KEY not configured")
            return False

        try:
            payload = {
                "to": device_token,
                "notification": {
                    "title": notification.get("title", ""),
                    "body": notification.get("body", ""),
                    "sound": "default"
                },
                "data": notification.get("data", {}),
                "priority": "high"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.fcm_api_url,
                    headers={
                        "Authorization": f"key={self.fcm_server_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success") == 1:
                        logger.info(f"Successfully sent FCM notification to device")
                        return True
                    else:
                        logger.error(f"FCM error: {result}")
                        return False
                else:
                    logger.error(f"FCM HTTP error: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send FCM notification: {e}")
            return False


class NtfyClient:
    """Client for sending push notifications via self-hosted ntfy server"""

    def __init__(self):
        self.ntfy_server_url = os.getenv("NTFY_SERVER_URL", "http://localhost:8080")
        self.ntfy_auth_token = os.getenv("NTFY_AUTH_TOKEN")

    async def send(self, topic: str, notification: Dict) -> bool:
        """
        Send push notification via ntfy

        Args:
            topic: ntfy topic (typically user-specific)
            notification: Dict with 'title' and 'body' keys

        Returns:
            True if successful, False otherwise
        """
        try:
            headers = {"Content-Type": "application/json"}
            if self.ntfy_auth_token:
                headers["Authorization"] = f"Bearer {self.ntfy_auth_token}"

            payload = {
                "topic": topic,
                "title": notification.get("title", ""),
                "message": notification.get("body", ""),
                "priority": notification.get("priority", 4),
                "tags": notification.get("tags", []),
                "click": notification.get("click_url"),
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ntfy_server_url}",
                    headers=headers,
                    json=payload,
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
    """Main service for sending push notifications to all platforms"""

    def __init__(self):
        self.apns_client = APNsClient()
        self.fcm_client = FCMClient()
        self.ntfy_client = NtfyClient()

    async def send_to_user(self, user_id: int, notification: Dict) -> Dict[str, int]:
        """
        Send notification to all registered devices for a user

        Args:
            user_id: User ID from database
            notification: Dict with 'title', 'body', and optional 'data'

        Returns:
            Dict with success/failure counts
        """
        from src.domain.device import Device
        from src.domain.user import User

        # Get all active devices for user
        devices = Device.select().where(
            (Device.user == user_id) &
            (Device.is_active == True)
        )

        results = {
            "sent": 0,
            "failed": 0,
            "total": 0
        }

        for device in devices:
            results["total"] += 1
            success = await self.send_to_device(device, notification)
            if success:
                results["sent"] += 1
            else:
                results["failed"] += 1

        logger.info(f"Sent notifications to user {user_id}: {results}")
        return results

    async def send_to_device(self, device, notification: Dict) -> bool:
        """
        Send notification to a specific device

        Args:
            device: Device model instance
            notification: Dict with notification content

        Returns:
            True if successful, False otherwise
        """
        try:
            if device.platform == "ios":
                if device.push_token:
                    return await self.apns_client.send(device.push_token, notification)
                else:
                    logger.warning(f"iOS device {device.id} has no push token")
                    return False

            elif device.platform == "android":
                if device.has_gms and device.push_token:
                    return await self.fcm_client.send(device.push_token, notification)
                elif device.ntfy_endpoint:
                    # Extract topic from endpoint or use device-specific topic
                    topic = self._extract_ntfy_topic(device.ntfy_endpoint)
                    return await self.ntfy_client.send(topic, notification)
                else:
                    logger.warning(f"Android device {device.id} has no valid push configuration")
                    return False
            else:
                logger.error(f"Unknown platform: {device.platform}")
                return False

        except Exception as e:
            logger.error(f"Error sending to device {device.id}: {e}")
            return False

    def _extract_ntfy_topic(self, endpoint: str) -> str:
        """Extract topic name from ntfy endpoint URL"""
        # endpoint format: http://ntfy.example.com/user_123_device_456
        return endpoint.split("/")[-1]

    async def send_to_all_users(self, notification: Dict, user_filter=None) -> Dict[str, int]:
        """
        Send notification to all users (or filtered subset)

        Args:
            notification: Notification content
            user_filter: Optional filter function for users

        Returns:
            Aggregate results
        """
        from src.domain.user import User

        users = User.select()
        if user_filter:
            users = users.where(user_filter)

        total_results = {"sent": 0, "failed": 0, "total": 0}

        for user in users:
            results = await self.send_to_user(user.id, notification)
            total_results["sent"] += results["sent"]
            total_results["failed"] += results["failed"]
            total_results["total"] += results["total"]

        return total_results


# Singleton instance
push_service = PushNotificationService()
