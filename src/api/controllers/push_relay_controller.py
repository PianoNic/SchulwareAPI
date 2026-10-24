import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from src.api.controller import controller
from src.application.dtos.push_relay_dtos import PushListenRequestDto, PushListenStatusDto, PushRegistrationDto
from src.application.services.push_relay_service import PushRelayError, push_relay

router = APIRouter(prefix="/api/push", tags=["Push Relay"])


def require_relay_key(x_push_relay_key: str | None = Header(default=None)) -> None:
    """The relay is off unless PUSH_RELAY_KEY is set, and then needs that key."""
    expected = os.getenv("PUSH_RELAY_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="Push relay is disabled on this server.")
    if not x_push_relay_key or not hmac.compare_digest(x_push_relay_key, expected):
        raise HTTPException(status_code=401, detail="Invalid push relay key.")


@controller(router)
class PushRelayController:
    @router.post("/register", response_model=PushRegistrationDto, dependencies=[Depends(require_relay_key)])
    async def register(self):
        """Create Firebase credentials for Schulnetz's push project and return their FCM token."""
        credentials, token = await push_relay.register()
        return PushRegistrationDto(credentials=credentials, token=token)

    @router.post("/listen", dependencies=[Depends(require_relay_key)])
    async def listen(self, body: PushListenRequestDto):
        """Start forwarding pushes for these credentials to the callback URL. Idempotent."""
        try:
            started = await push_relay.listen(body.listener_id, body.credentials, body.callback_url, body.callback_secret)
        except PushRelayError as ex:
            raise HTTPException(status_code=400, detail=str(ex))
        return {"started": started}

    @router.get("/listen/{listener_id}", response_model=PushListenStatusDto, operation_id="push-listen-status", dependencies=[Depends(require_relay_key)])
    async def status(self, listener_id: str):
        current = push_relay.status(listener_id)
        return PushListenStatusDto(running=False) if current is None else PushListenStatusDto(**current)

    @router.delete("/listen/{listener_id}", status_code=204, operation_id="push-listen-stop", dependencies=[Depends(require_relay_key)])
    async def stop(self, listener_id: str):
        await push_relay.stop(listener_id)
        return Response(status_code=204)
