from pydantic import BaseModel, Field
from typing import Optional


class DeviceRegistrationRequest(BaseModel):
    """DTO for registering a device for push notifications"""
    platform: str = Field(..., description="Platform: 'ios' or 'android'")
    has_gms: bool = Field(default=True, description="Whether device has Google Mobile Services")
    push_token: Optional[str] = Field(None, description="APNs token (iOS) or FCM token (Android with GMS)")
    ntfy_endpoint: Optional[str] = Field(None, description="ntfy endpoint for UnifiedPush (Android without GMS)")
    device_name: Optional[str] = Field(None, description="Optional device name for user reference")

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "ios",
                "push_token": "abc123...",
                "device_name": "iPhone 14 Pro"
            }
        }


class DeviceRegistrationResponse(BaseModel):
    """Response after successful device registration"""
    device_id: int
    message: str
    ntfy_topic: Optional[str] = Field(None, description="ntfy topic for UnifiedPush users")


class DeviceDto(BaseModel):
    """DTO for device information"""
    id: int
    platform: str
    has_gms: bool
    device_name: Optional[str]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True
