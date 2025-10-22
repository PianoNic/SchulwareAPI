from fastapi import Depends, HTTPException, status
from typing import List
from src.application.dtos.device_registration_dto import (
    DeviceRegistrationRequest,
    DeviceRegistrationResponse,
    DeviceDto
)
from src.api.auth.token_dependency import get_current_token
from src.api.auth.bearer import security
from src.api.router_registry import SchulwareAPIRouter
from src.domain.device import Device
from src.domain.user import User
from src.application.services.token_service import decode_jwt_token
import logging

logger = logging.getLogger(__name__)

router = SchulwareAPIRouter()


@router.post("register", dependencies=[Depends(security)], response_model=DeviceRegistrationResponse)
async def register_device(
    request: DeviceRegistrationRequest,
    token: str = Depends(get_current_token)
):
    """
    Register a device for push notifications.

    - **iOS**: Provide platform='ios' and push_token (APNs device token)
    - **Android with Google**: Provide platform='android', has_gms=true, push_token (FCM token)
    - **Android without Google**: Provide platform='android', has_gms=false, ntfy_endpoint (UnifiedPush endpoint)
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

        # Validate request
        if request.platform not in ["ios", "android"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform must be 'ios' or 'android'"
            )

        if request.platform == "ios" and not request.push_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="iOS devices must provide push_token"
            )

        if request.platform == "android":
            if request.has_gms and not request.push_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Android devices with GMS must provide push_token"
                )
            if not request.has_gms and not request.ntfy_endpoint:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Android devices without GMS must provide ntfy_endpoint"
                )

        # Check if device already exists (same user + platform + token)
        existing_device = None
        if request.push_token:
            existing_device = Device.get_or_none(
                (Device.user == user) &
                (Device.platform == request.platform) &
                (Device.push_token == request.push_token)
            )
        elif request.ntfy_endpoint:
            existing_device = Device.get_or_none(
                (Device.user == user) &
                (Device.platform == request.platform) &
                (Device.ntfy_endpoint == request.ntfy_endpoint)
            )

        if existing_device:
            # Update existing device
            existing_device.is_active = True
            existing_device.has_gms = request.has_gms
            if request.device_name:
                existing_device.device_name = request.device_name
            existing_device.save()

            logger.info(f"Updated existing device {existing_device.id} for user {user.email}")

            return DeviceRegistrationResponse(
                device_id=existing_device.id,
                message="Device updated successfully",
                ntfy_topic=f"schulware_user_{user.id}" if not request.has_gms else None
            )

        # Create new device
        device = Device.create(
            user=user,
            platform=request.platform,
            has_gms=request.has_gms,
            push_token=request.push_token,
            ntfy_endpoint=request.ntfy_endpoint,
            device_name=request.device_name,
            is_active=True
        )

        logger.info(f"Registered new device {device.id} for user {user.email} (platform: {request.platform})")

        return DeviceRegistrationResponse(
            device_id=device.id,
            message="Device registered successfully",
            ntfy_topic=f"schulware_user_{user.id}" if not request.has_gms else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device"
        )


@router.get("devices", dependencies=[Depends(security)], response_model=List[DeviceDto])
async def get_user_devices(token: str = Depends(get_current_token)):
    """Get all registered devices for the current user"""
    try:
        payload = decode_jwt_token(token)
        user_email = payload.get("sub")

        user = User.get_or_none(User.email == user_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        devices = Device.select().where(
            (Device.user == user) &
            (Device.is_active == True)
        )

        return [
            DeviceDto(
                id=device.id,
                platform=device.platform,
                has_gms=device.has_gms,
                device_name=device.device_name,
                is_active=device.is_active,
                created_at=device.created_at.isoformat()
            )
            for device in devices
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch devices"
        )


@router.delete("devices/{device_id}", dependencies=[Depends(security)])
async def unregister_device(device_id: int, token: str = Depends(get_current_token)):
    """Unregister a device (soft delete)"""
    try:
        payload = decode_jwt_token(token)
        user_email = payload.get("sub")

        user = User.get_or_none(User.email == user_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        device = Device.get_or_none(
            (Device.id == device_id) &
            (Device.user == user)
        )

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        device.is_active = False
        device.save()

        logger.info(f"Unregistered device {device_id} for user {user.email}")

        return {"message": "Device unregistered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unregistering device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unregister device"
        )
