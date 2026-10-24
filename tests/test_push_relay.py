"""Push relay: registration, listener lifecycle, signed forwarding and callback-URL rules, with a fake Firebase client."""

import asyncio
import json

import httpx
import pytest

from src.application.services import push_relay_service as relay_module
from src.application.services.push_relay_service import PushRelay, PushRelayError, is_allowed_callback, sign

CALLBACK = "https://backend.example.ch/api/plugins/schulware/push/abc"
SECRET = "0123456789abcdef-secret"


class FakeClient:
    instances = []

    def __init__(self, on_push, config, credentials, on_credentials):
        self.on_push = on_push
        self.credentials = credentials
        self.on_credentials = on_credentials
        self.started = False
        FakeClient.instances.append(self)

    async def checkin_or_register(self):
        if not self.credentials:
            self.on_credentials({"fcm": {"token": "fcm-token"}, "keys": {"private": "k"}})
        return "fcm-token"

    async def start(self):
        self.started = True

    async def stop(self):
        self.started = False

    def is_started(self):
        return self.started


@pytest.fixture(autouse=True)
def reset_fakes():
    FakeClient.instances.clear()


def relay(received=None, status=200, max_listeners=10):
    def handler(request: httpx.Request) -> httpx.Response:
        if received is not None:
            received.append(request)
        return httpx.Response(status)

    return PushRelay(client_factory=FakeClient, http=httpx.AsyncClient(transport=httpx.MockTransport(handler)), max_listeners=max_listeners)


@pytest.mark.asyncio
async def test_register_returns_the_new_credentials_and_token():
    credentials, token = await relay().register()
    assert token == "fcm-token"
    assert credentials["fcm"]["token"] == "fcm-token"


@pytest.mark.asyncio
async def test_a_push_is_forwarded_with_a_valid_signature():
    received = []
    r = relay(received)
    assert await r.listen("account-1", {"fcm": {}}, CALLBACK, SECRET)

    FakeClient.instances[-1].on_push({"notification": {"title": "Neue Note"}}, "pid-1")
    await asyncio.sleep(0.05)

    assert len(received) == 1
    body = received[0].content
    assert received[0].headers["X-Schulware-Signature"] == sign(SECRET, body)
    assert json.loads(body) == {"listener_id": "account-1", "persistent_id": "pid-1", "notification": {"notification": {"title": "Neue Note"}}}


@pytest.mark.asyncio
async def test_listening_again_with_the_same_settings_is_a_no_op():
    r = relay()
    assert await r.listen("account-1", {"fcm": {}}, CALLBACK, SECRET)
    assert not await r.listen("account-1", {"fcm": {}}, CALLBACK, SECRET)
    assert len(FakeClient.instances) == 1


@pytest.mark.asyncio
async def test_a_new_callback_replaces_the_listener():
    r = relay()
    await r.listen("account-1", {"fcm": {}}, CALLBACK, SECRET)
    await r.listen("account-1", {"fcm": {}}, CALLBACK + "-new", SECRET)
    assert not FakeClient.instances[0].started
    assert FakeClient.instances[1].started


@pytest.mark.asyncio
async def test_stop_closes_the_connection():
    r = relay()
    await r.listen("account-1", {"fcm": {}}, CALLBACK, SECRET)
    assert await r.stop("account-1")
    assert not FakeClient.instances[0].started
    assert r.status("account-1") is None


@pytest.mark.asyncio
async def test_capacity_is_enforced():
    r = relay(max_listeners=1)
    await r.listen("account-1", {"fcm": {}}, CALLBACK, SECRET)
    with pytest.raises(PushRelayError, match="capacity"):
        await r.listen("account-2", {"fcm": {}}, CALLBACK, SECRET)


@pytest.mark.asyncio
async def test_a_private_callback_is_refused_unless_allowed(monkeypatch):
    monkeypatch.delenv("PUSH_CALLBACK_ALLOWED_HOSTS", raising=False)
    with pytest.raises(PushRelayError, match="allowed"):
        await relay().listen("account-1", {"fcm": {}}, "http://127.0.0.1:5033/hook", SECRET)

    monkeypatch.setenv("PUSH_CALLBACK_ALLOWED_HOSTS", "host.docker.internal")
    assert is_allowed_callback("http://host.docker.internal:5033/hook")
    assert not is_allowed_callback("http://169.254.169.254/latest")


def test_the_relay_controller_is_disabled_without_a_key(monkeypatch):
    from fastapi.testclient import TestClient

    from src.api.app import app

    monkeypatch.delenv("PUSH_RELAY_KEY", raising=False)
    client = TestClient(app)
    assert client.post("/api/push/register").status_code == 503

    monkeypatch.setenv("PUSH_RELAY_KEY", "relay-key")
    assert client.post("/api/push/register", headers={"X-Push-Relay-Key": "wrong"}).status_code == 401
