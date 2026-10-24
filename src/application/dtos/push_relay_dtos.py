from pydantic import BaseModel, Field


class PushRegistrationDto(BaseModel):
    credentials: dict = Field(..., description="Firebase credentials for Schulnetz's push project. Store them; send them back to /listen.")
    token: str = Field(..., description="FCM token to file at Schulnetz via POST /api/mobile/notifications/token.")


class PushListenRequestDto(BaseModel):
    listener_id: str = Field(..., min_length=1, max_length=200, description="Caller-chosen id, e.g. the account id.")
    credentials: dict = Field(..., description="Credentials from /register (or the latest ones from GET /listen/{id}).")
    callback_url: str = Field(..., description="Receives each push as JSON, signed in the X-Schulware-Signature header.")
    callback_secret: str = Field(..., min_length=16, description="HMAC-SHA256 key for the signature.")


class PushListenStatusDto(BaseModel):
    running: bool
    credentials: dict | None = None
