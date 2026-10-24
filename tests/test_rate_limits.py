"""Rate limits: trusted-proxy IP resolution, the backend service key, and per-token mobile buckets."""

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from src.api import rate_limit
from src.api.rate_limit import (
    SERVICE_KEY_HEADER,
    ServiceCallerMiddleware,
    get_client_ip,
    is_service_caller,
    limit_per_token,
    require_service_key,
    shared_limiter,
    shared_rate_limit_exceeded_handler,
)

KEY = "backend-service-key"


def _request(peer: str, headers: dict[str, str] | None = None) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "client": (peer, 1234), "headers": raw})


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("SERVICE_API_KEY", raising=False)
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    shared_limiter.reset()


def test_forwarded_for_from_public_peer_is_ignored():
    assert get_client_ip(_request("8.8.8.8", {"X-Forwarded-For": "1.2.3.4"})) == "8.8.8.8"


def test_forwarded_for_from_private_proxy_is_honored():
    assert get_client_ip(_request("172.18.0.5", {"X-Forwarded-For": "1.2.3.4, 172.18.0.5"})) == "1.2.3.4"


def test_trusted_proxies_override_the_private_default(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXIES", "198.51.100.0/24")
    assert get_client_ip(_request("198.51.100.9", {"X-Real-IP": "1.2.3.4"})) == "1.2.3.4"
    assert get_client_ip(_request("10.0.0.2", {"X-Real-IP": "1.2.3.4"})) == "10.0.0.2"


def test_login_is_open_without_a_configured_key():
    require_service_key(_request("8.8.8.8"))


def test_login_requires_the_configured_key(monkeypatch):
    monkeypatch.setenv("SERVICE_API_KEY", KEY)
    with pytest.raises(HTTPException) as denied:
        require_service_key(_request("8.8.8.8", {SERVICE_KEY_HEADER: "wrong"}))
    assert denied.value.status_code == 401
    require_service_key(_request("8.8.8.8", {SERVICE_KEY_HEADER: KEY}))


def _limited_app() -> TestClient:
    limiter = Limiter(key_func=get_client_ip)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, shared_rate_limit_exceeded_handler)
    app.add_middleware(ServiceCallerMiddleware)

    @app.get("/limited")
    @limiter.limit("2/minute", exempt_when=is_service_caller)
    async def limited(request: Request):
        return {"ok": True}

    return TestClient(app)


def test_anonymous_callers_share_their_ip_bucket():
    client = _limited_app()
    codes = [client.get("/limited").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_backend_with_service_key_is_never_throttled_by_ip(monkeypatch):
    monkeypatch.setenv("SERVICE_API_KEY", KEY)
    client = _limited_app()
    codes = {client.get("/limited", headers={SERVICE_KEY_HEADER: KEY}).status_code for _ in range(200)}
    assert codes == {200}


def test_a_wrong_service_key_gets_no_exemption(monkeypatch):
    monkeypatch.setenv("SERVICE_API_KEY", KEY)
    client = _limited_app()
    codes = [client.get("/limited", headers={SERVICE_KEY_HEADER: "nope"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def _mobile_app() -> TestClient:
    app = FastAPI()

    @app.get("/mobile", dependencies=[Depends(limit_per_token)])
    async def mobile():
        return {"ok": True}

    return TestClient(app)


def test_each_token_gets_its_own_bucket():
    client = _mobile_app()
    alice = {"Authorization": "Bearer alice"}
    assert all(client.get("/mobile", headers=alice).status_code == 200 for _ in range(60))
    assert client.get("/mobile", headers=alice).status_code == 429
    assert client.get("/mobile", headers={"Authorization": "Bearer bob"}).status_code == 200


def test_hundreds_of_users_from_one_ip_are_not_throttled_together():
    client = _mobile_app()
    codes = {client.get("/mobile", headers={"Authorization": f"Bearer user-{n}"}).status_code for n in range(500)}
    assert codes == {200}
