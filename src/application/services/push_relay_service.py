"""Relays Schulnetz push notifications to a caller's webhook.

Schulnetz pushes go through its own Firebase project. `register` creates Firebase
credentials for that project (the caller then files the resulting token at Schulnetz via
`POST /me/notifications/token`), and `listen` keeps a connection per listener id open and
POSTs every push to the caller's callback URL, signed with HMAC-SHA256 over the body.
The caller owns the credentials and re-sends them; only live connections are in memory.
"""

import asyncio
import hashlib
import hmac
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from firebase_messaging import FcmPushClient, FcmRegisterConfig

from src.api.url_guard import is_safe_base_url
from src.infrastructure.logging_config import get_logger

logger = get_logger("push_relay")

SCHULNETZ_PUSH_CONFIG = FcmRegisterConfig(
    project_id="schulnetz",
    app_id="1:291184162579:web:26a69526ed3aef4e770ce6",
    api_key="AIzaSyAabYK6tQWW2_BBlOgFdiVlB7F2XdKU1G8",
    messaging_sender_id="291184162579",
)
SIGNATURE_HEADER = "X-Schulware-Signature"


class PushRelayError(Exception):
    pass


def sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def is_allowed_callback(url: str) -> bool:
    """A public http(s) URL, or one whose host the operator allowed via PUSH_CALLBACK_ALLOWED_HOSTS."""
    allowed = {h.strip().lower() for h in os.getenv("PUSH_CALLBACK_ALLOWED_HOSTS", "").split(",") if h.strip()}
    parsed = urlparse(url or "")
    if parsed.scheme in ("http", "https") and (parsed.hostname or "").lower() in allowed:
        return True
    return is_safe_base_url(url)


@dataclass
class _Listener:
    callback_url: str
    secret: str
    credentials: dict
    client: object | None = None


class PushRelay:
    def __init__(self, client_factory: Callable = FcmPushClient, config: FcmRegisterConfig = SCHULNETZ_PUSH_CONFIG, http: httpx.AsyncClient | None = None, max_listeners: int | None = None):
        self._factory = client_factory
        self._config = config
        self._http = http
        self._max = max_listeners if max_listeners is not None else int(os.getenv("PUSH_RELAY_MAX_LISTENERS", "500"))
        self._listeners: dict[str, _Listener] = {}
        self._lock = asyncio.Lock()

    async def register(self) -> tuple[dict, str]:
        """New Firebase credentials for Schulnetz's push project, and their FCM token."""
        saved: dict = {}
        client = self._factory(lambda *_: None, self._config, None, saved.update)
        token = await client.checkin_or_register()
        return saved, token

    async def listen(self, listener_id: str, credentials: dict, callback_url: str, secret: str) -> bool:
        """Start (or replace) the listener; False when an identical one is already running."""
        if not is_allowed_callback(callback_url):
            raise PushRelayError("callback_url is not an allowed target")
        async with self._lock:
            current = self._listeners.get(listener_id)
            if current and current.callback_url == callback_url and current.secret == secret and self._running(current):
                return False
            if current:
                await self._stop(current)
                del self._listeners[listener_id]
            if len(self._listeners) >= self._max:
                raise PushRelayError("push relay is at capacity")

            listener = _Listener(callback_url, secret, dict(credentials))
            listener.client = self._factory(lambda notification, persistent_id, obj=None: self._schedule(listener_id, listener, notification, persistent_id), self._config, listener.credentials, listener.credentials.update)
            await listener.client.checkin_or_register()
            await listener.client.start()
            self._listeners[listener_id] = listener
            logger.info("push relay: listening for %s (%d active)", listener_id, len(self._listeners))
            return True

    async def stop(self, listener_id: str) -> bool:
        async with self._lock:
            listener = self._listeners.pop(listener_id, None)
            if listener is None:
                return False
            await self._stop(listener)
            return True

    def status(self, listener_id: str) -> dict | None:
        """Whether the listener runs, plus its current credentials (Firebase may rotate them)."""
        listener = self._listeners.get(listener_id)
        if listener is None:
            return None
        return {"running": self._running(listener), "credentials": listener.credentials}

    def _schedule(self, listener_id: str, listener: _Listener, notification: dict, persistent_id: str) -> None:
        asyncio.get_running_loop().create_task(self._forward(listener_id, listener, notification, persistent_id))

    async def _forward(self, listener_id: str, listener: _Listener, notification: dict, persistent_id: str) -> None:
        body = json.dumps({"listener_id": listener_id, "persistent_id": persistent_id, "notification": notification}).encode()
        headers = {"Content-Type": "application/json", SIGNATURE_HEADER: sign(listener.secret, body)}
        http = self._http or httpx.AsyncClient(timeout=15.0)
        try:
            for attempt in range(3):
                try:
                    response = await http.post(listener.callback_url, content=body, headers=headers)
                    if response.status_code < 500:
                        logger.info("push relay: forwarded %s for %s (%d)", persistent_id, listener_id, response.status_code)
                        return
                except httpx.HTTPError as ex:
                    logger.warning("push relay: callback for %s failed: %s", listener_id, ex)
                await asyncio.sleep(2 ** attempt)
            logger.error("push relay: gave up forwarding %s for %s", persistent_id, listener_id)
        finally:
            if self._http is None:
                await http.aclose()

    @staticmethod
    def _running(listener: _Listener) -> bool:
        return listener.client is not None and listener.client.is_started()

    @staticmethod
    async def _stop(listener: _Listener) -> None:
        if PushRelay._running(listener):
            try:
                await listener.client.stop()
            except Exception as ex:
                logger.warning("push relay: stopping a listener failed: %s", ex)


push_relay = PushRelay()
