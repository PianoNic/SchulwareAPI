"""Native (non-Microsoft) Schulnetz login, driven against a fake Schulnetz over httpx.MockTransport.

The pages mimic the protocol seen in community clients: a login form with a hidden
`loginhash` plus `login` / `passwort`, an optional `pin` form for 2FA, a redirect carrying
the OAuth `code` on the mobile leg, and a dashboard with id/transid links on the web leg.
"""

from urllib.parse import parse_qs

import httpx
import pytest

from src.application.services import native_login_service as native
from src.application.services.web_session_service import _is_login_page

BASE = "https://schulnetz.example.ch"

LOGIN_FORM = """<html><body>
<div class="mdl-cell" style="color:#ffb138">{error}</div>
<form id="standardformular" method="post" action="{action}">
  <input type="hidden" name="loginhash" value="h4sh">
  <input type="text" name="login"><input type="password" name="passwort">
  <input type="submit" value="Anmelden">
</form></body></html>"""

PIN_FORM = """<html><body><form method="post" action="index.php?pageid=pin">
  <input type="hidden" name="loginhash" value="h4sh2"><input type="text" name="pin">
</form></body></html>"""

DASHBOARD = '<html><body><a href="index.php?pageid=21311&id=abc123&transid=def456">Noten</a></body></html>'


def school(password="secret", pin=None):
    """A fake Schulnetz; returns (transport, list of received form bodies)."""
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        path, query = request.url.path, request.url.params
        if request.method == "POST":
            body = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            posts.append(body)
            if "pin" in body:
                ok = body["pin"] == pin
                return httpx.Response(302, headers={"location": "?code=the-code&state=s" if ok else "/authorize.php?error=pin"})
            if body.get("passwort") != password or body.get("loginhash") != "h4sh":
                return httpx.Response(302, headers={"location": f"{path}?mode=1"})
            if pin is not None:
                return httpx.Response(200, text=PIN_FORM)
            if path.endswith("/index.php"):
                return httpx.Response(302, headers={"location": "index.php?pageid=1", "set-cookie": "PHPSESSID=php-session; Path=/"})
            return httpx.Response(302, headers={"location": "?code=the-code&state=s"})
        if path.endswith("/authorize.php"):
            error = "Benutzername oder Passwort falsch" if query.get("mode") else ""
            return httpx.Response(200, text=LOGIN_FORM.format(action="authorize.php", error=error))
        if path.endswith("/loginto.php"):
            error = "Benutzername oder Passwort falsch" if query.get("mode") else ""
            return httpx.Response(200, text=LOGIN_FORM.format(action="index.php", error=error), headers={"set-cookie": "PHPSESSID=anon; Path=/"})
        if path.endswith("/index.php") and query.get("mode"):
            return httpx.Response(302, headers={"location": "loginto.php?mode=1"})
        if path.endswith("/index.php"):
            return httpx.Response(200, text=DASHBOARD)
        return httpx.Response(404)

    return httpx.MockTransport(handler), posts


@pytest.fixture
def token_exchange(monkeypatch):
    seen = {}

    async def fake_exchange(code, verifier, base_url):
        seen["code"] = code
        return "access-token", "refresh-token"

    monkeypatch.setattr(native, "exchange_code_for_tokens", fake_exchange)
    return seen


@pytest.mark.asyncio
async def test_detects_a_native_login_school():
    transport, _ = school()
    assert await native.detect_login_mode(BASE, transport=transport) == "native"


@pytest.mark.asyncio
async def test_detects_a_microsoft_school():
    transport = httpx.MockTransport(lambda r: httpx.Response(302, headers={"location": "https://login.microsoftonline.com/common/oauth2/authorize?x=1"}))
    assert await native.detect_login_mode(BASE, transport=transport) == "microsoft"


@pytest.mark.asyncio
async def test_mobile_leg_exchanges_the_code_from_the_redirect(token_exchange):
    transport, posts = school()

    tokens = await native.native_mobile_tokens(BASE, "alex@school.ch", "secret", None, transport=transport)

    assert tokens == ("access-token", "refresh-token")
    assert token_exchange["code"] == "the-code"
    assert posts[0] == {"loginhash": "h4sh", "login": "alex@school.ch", "passwort": "secret"}


@pytest.mark.asyncio
async def test_mobile_leg_answers_the_pin_step(token_exchange):
    transport, posts = school(pin="123456")

    await native.native_mobile_tokens(BASE, "alex@school.ch", "secret", "123456", transport=transport)

    assert posts[-1]["pin"] == "123456"
    assert token_exchange["code"] == "the-code"


@pytest.mark.asyncio
async def test_pin_step_without_a_secret_fails_clearly(token_exchange):
    transport, _ = school(pin="123456")

    with pytest.raises(native.NativeLoginFailed, match="2FA"):
        await native.native_mobile_tokens(BASE, "alex@school.ch", "secret", None, transport=transport)


@pytest.mark.asyncio
async def test_wrong_password_reports_the_schools_message(token_exchange):
    transport, _ = school()

    with pytest.raises(native.NativeLoginFailed, match="Passwort falsch"):
        await native.native_mobile_tokens(BASE, "alex@school.ch", "wrong", None, transport=transport)


@pytest.mark.asyncio
async def test_web_leg_captures_session_and_ids():
    transport, _ = school()

    cookies, info = await native.native_web_session(BASE, "alex@school.ch", "secret", None, transport=transport)

    assert cookies["PHPSESSID"] == "php-session"
    assert (info["id"], info["transid"]) == ("abc123", "def456")


@pytest.mark.asyncio
async def test_web_leg_wrong_password_fails():
    transport, _ = school()

    with pytest.raises(native.NativeLoginFailed):
        await native.native_web_session(BASE, "alex@school.ch", "wrong", None, transport=transport)


def test_totp_code_accepts_an_otpauth_uri(monkeypatch):
    monkeypatch.setattr(native, "totp_now", lambda secret: f"code-for-{secret}")

    assert native.totp_code_for("otpauth://totp/Schulnetz:alex?secret=jbsw y3dp&issuer=Schulnetz", None) == "code-for-JBSWY3DP"
    assert native.totp_code_for("JBSWY3DP", " 654321 ") == "654321"
    assert native.totp_code_for(None, None) is None


def test_loginto_counts_as_an_expired_session():
    assert _is_login_page(f"{BASE}/loginto.php?mode=0")
    assert _is_login_page("https://login.microsoftonline.com/x")
    assert not _is_login_page(f"{BASE}/index.php?pageid=21311")


@pytest.mark.asyncio
async def test_detects_a_school_with_another_sign_in_as_browser():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text='<form><input name="userid"><input name="password"></form>'))
    assert await native.detect_login_mode(BASE, transport=transport) == "browser"
