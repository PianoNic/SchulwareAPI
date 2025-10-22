"""
Background service to watch for new Schulnetz notifications and send push notifications.

This is an optional service that polls Schulnetz for new notifications and sends
push notifications to users when new content is available.

Usage:
    # Run as a background task
    import asyncio
    from src.application.services.notification_watcher_service import notification_watcher

    asyncio.create_task(notification_watcher.start())
"""

import asyncio
import logging
from typing import Dict, Set
from datetime import datetime, timedelta
from src.application.services.push_notification_service import push_service
from src.domain.user import User
from src.domain.auth import MobileSession

logger = logging.getLogger(__name__)


class NotificationWatcher:
    """Watches for new Schulnetz notifications and triggers push notifications"""

    def __init__(self, poll_interval: int = 300):
        """
        Initialize the notification watcher

        Args:
            poll_interval: How often to check for new notifications (seconds)
        """
        self.poll_interval = poll_interval
        self.running = False
        self.last_checked: Dict[int, datetime] = {}  # user_id -> last check time

    async def start(self):
        """Start the background watcher service"""
        if self.running:
            logger.warning("Notification watcher already running")
            return

        self.running = True
        logger.info(f"Starting notification watcher (poll interval: {self.poll_interval}s)")

        try:
            while self.running:
                await self._check_all_users()
                await asyncio.sleep(self.poll_interval)
        except Exception as e:
            logger.error(f"Notification watcher crashed: {e}")
            self.running = False
            raise

    def stop(self):
        """Stop the background watcher service"""
        logger.info("Stopping notification watcher")
        self.running = False

    async def _check_all_users(self):
        """Check all users for new notifications"""
        try:
            # Get all users with active mobile sessions
            users = User.select().join(MobileSession).where(
                MobileSession.access_token.is_null(False)
            )

            logger.debug(f"Checking {len(list(users))} users for new notifications")

            for user in users:
                try:
                    await self._check_user_notifications(user)
                except Exception as e:
                    logger.error(f"Error checking user {user.email}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in _check_all_users: {e}")

    async def _check_user_notifications(self, user: User):
        """
        Check a specific user for new notifications

        Args:
            user: User to check
        """
        # Get user's mobile session
        mobile_session = MobileSession.get_or_none(MobileSession.user == user)
        if not mobile_session or not mobile_session.access_token:
            return

        # Get last check time
        last_check = self.last_checked.get(user.id)

        # Fetch notifications from Schulnetz
        # NOTE: You'll need to implement this based on your existing proxy logic
        new_notifications = await self._fetch_schulnetz_notifications(
            mobile_session.access_token,
            since=last_check
        )

        # Send push notifications for new items
        for notification in new_notifications:
            await self._send_push_notification(user.id, notification)

        # Update last check time
        self.last_checked[user.id] = datetime.now()

    async def _fetch_schulnetz_notifications(self, access_token: str, since: datetime = None):
        """
        Fetch notifications from Schulnetz API

        Args:
            access_token: User's Schulnetz access token
            since: Only fetch notifications after this time

        Returns:
            List of new notifications

        TODO: Implement this based on your existing proxy logic
        """
        # Example implementation - you'll need to adapt this to your actual API
        from src.application.queries.proxy_mobile_rest_query import proxy_mobile_rest_query_async

        try:
            # Fetch notifications from Schulnetz
            notifications = await proxy_mobile_rest_query_async(
                access_token,
                "me/notifications/push",
                "GET"
            )

            # Filter for new notifications
            # You'll need to implement logic to determine what's "new"
            # This could be based on timestamp, ID comparison, etc.

            new_notifications = []
            # TODO: Add filtering logic here based on 'since' parameter

            return new_notifications

        except Exception as e:
            logger.error(f"Error fetching Schulnetz notifications: {e}")
            return []

    async def _send_push_notification(self, user_id: int, notification_data: dict):
        """
        Send push notification to user

        Args:
            user_id: User ID to send to
            notification_data: Notification data from Schulnetz
        """
        try:
            # Convert Schulnetz notification format to our push notification format
            push_notification = {
                "title": notification_data.get("title", "New Notification"),
                "body": notification_data.get("body", "You have a new notification"),
                "data": {
                    "type": "schulnetz_notification",
                    "notification_id": notification_data.get("id"),
                    "timestamp": notification_data.get("timestamp"),
                }
            }

            # Send to all user's devices
            results = await push_service.send_to_user(user_id, push_notification)

            logger.info(
                f"Sent notification to user {user_id}: "
                f"{results['sent']} devices, {results['failed']} failed"
            )

        except Exception as e:
            logger.error(f"Error sending push notification: {e}")


# Example: Trigger notifications for specific events
class EventNotifier:
    """Helper class to send notifications for specific Schulnetz events"""

    @staticmethod
    async def notify_new_grade(user_id: int, grade_data: dict):
        """Send notification for new grade"""
        await push_service.send_to_user(
            user_id=user_id,
            notification={
                "title": "New Grade Available",
                "body": f"You received a grade in {grade_data.get('subject', 'a subject')}",
                "data": {
                    "type": "new_grade",
                    "grade_id": grade_data.get("id"),
                    "subject": grade_data.get("subject"),
                }
            }
        )

    @staticmethod
    async def notify_new_exam(user_id: int, exam_data: dict):
        """Send notification for new exam"""
        await push_service.send_to_user(
            user_id=user_id,
            notification={
                "title": "New Exam Scheduled",
                "body": f"Exam scheduled for {exam_data.get('subject', 'a subject')}",
                "data": {
                    "type": "new_exam",
                    "exam_id": exam_data.get("id"),
                    "subject": exam_data.get("subject"),
                    "date": exam_data.get("date"),
                }
            }
        )

    @staticmethod
    async def notify_new_absence(user_id: int, absence_data: dict):
        """Send notification for new absence record"""
        await push_service.send_to_user(
            user_id=user_id,
            notification={
                "title": "Absence Recorded",
                "body": f"An absence has been recorded for {absence_data.get('date', 'a date')}",
                "data": {
                    "type": "new_absence",
                    "absence_id": absence_data.get("id"),
                    "date": absence_data.get("date"),
                }
            }
        )

    @staticmethod
    async def notify_system_message(message: str, user_filter=None):
        """Send system-wide notification"""
        await push_service.send_to_all_users(
            notification={
                "title": "System Notification",
                "body": message,
                "data": {
                    "type": "system_message",
                }
            },
            user_filter=user_filter
        )


# Singleton instances
notification_watcher = NotificationWatcher(poll_interval=300)  # Check every 5 minutes
event_notifier = EventNotifier()


# Example usage in your app startup:
#
# from src.application.services.notification_watcher_service import notification_watcher
# import asyncio
#
# # In your FastAPI startup event:
# @app.on_event("startup")
# async def startup_event():
#     # Start the notification watcher in the background
#     asyncio.create_task(notification_watcher.start())
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     notification_watcher.stop()
