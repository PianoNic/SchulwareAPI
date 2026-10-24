from pydantic import BaseModel, Field

SCHULNETZ_PUSH_TYPE = "schulNetz-App-FCM-PROD"


class PushTokenRequestDto(BaseModel):
    token: str = Field(..., description="FCM registration token of Schulnetz's push project (from /api/push/register).")
    type: str = Field(default=SCHULNETZ_PUSH_TYPE, description="Device type Schulnetz files the token under.")


class PushTokenResultDto(BaseModel):
    id: str | None = None
    status: str | None = None
    message: str | None = None
