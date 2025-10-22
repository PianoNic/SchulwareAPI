from pydantic import BaseModel, Field
from typing import Optional, Dict


class SendNotificationRequest(BaseModel):
    """DTO for sending a push notification"""
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body/message")
    data: Optional[Dict] = Field(None, description="Additional data payload")
    badge: Optional[int] = Field(1, description="Badge count (iOS)")
    priority: Optional[int] = Field(4, description="Priority (ntfy: 1-5)")
    tags: Optional[list] = Field(None, description="Tags for ntfy notifications")
    click_url: Optional[str] = Field(None, description="URL to open on click")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "New Grade Available",
                "body": "You have a new grade in Mathematics",
                "data": {"grade_id": 123, "subject": "math"}
            }
        }


class SendNotificationResponse(BaseModel):
    """Response after sending notifications"""
    sent: int = Field(..., description="Number of devices that received the notification")
    failed: int = Field(..., description="Number of devices that failed to receive")
    total: int = Field(..., description="Total number of devices attempted")
