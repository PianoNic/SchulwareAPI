from fastapi import Depends, HTTPException, status
from src.application.dtos.send_notification_dto import (
    SendNotificationRequest,
    SendNotificationResponse
)
from src.api.auth.token_dependency import get_current_token
from src.api.auth.bearer import security
from src.api.router_registry import SchulwareAPIRouter
from src.application.services.push_notification_service import push_service
from src.application.services.token_service import decode_jwt_token
from src.domain.user import User
import logging

logger = logging.getLogger(__name__)

router = SchulwareAPIRouter()


@router.post("send", dependencies=[Depends(security)], response_model=SendNotificationResponse)
async def send_notification_to_self(
    request: SendNotificationRequest,
    token: str = Depends(get_current_token)
):
    """
    Send a push notification to all your registered devices.
    Useful for testing push notification setup.
    """
    try:
        # Decode JWT to get user email
        payload = decode_jwt_token(token)
        user_email = payload.get("sub")

        # Get user from database
        user = User.get_or_none(User.email == user_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prepare notification
        notification = {
            "title": request.title,
            "body": request.body,
            "data": request.data or {},
            "badge": request.badge,
            "priority": request.priority,
            "tags": request.tags or [],
            "click_url": request.click_url
        }

        # Send notification to all user's devices
        results = await push_service.send_to_user(user.id, notification)

        logger.info(f"Sent notification to user {user.email}: {results}")

        return SendNotificationResponse(
            sent=results["sent"],
            failed=results["failed"],
            total=results["total"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )
