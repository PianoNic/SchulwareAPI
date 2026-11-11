"""A Microsoft login whose mobile step is refused still returns the working web session."""

import pytest

from src.application.commands import refresh_token_command as cmd

BASE = "https://schulnetz.example.ch"
COOKIES = [{"domain": "login.microsoftonline.com", "name": "ESTSAUTH", "path": "/", "value": "v"}]


def patch(monkeypatch, mobile_error):
    async def discover(base):
        return "https://login.microsoftonline.com/web", {"PHPSESSID": "anon"}

    async def login(self, url, command, cookies, ms_redirect=False):
        if ms_redirect:
            return {"redirect_url": BASE + "/?code=web", "session_cookies": cookies}
        if mobile_error:
            raise mobile_error
        return {"code": "mobile", "session_cookies": cookies}

    async def capture(base, callback_url, seed_cookies=None):
        return {"PHPSESSID": "php"}, {"id": "42", "transid": "t1"}

    async def exchange(code, verifier, base):
        return "access", "refresh"

    monkeypatch.setattr(cmd, "discover_web_oauth", discover)
    monkeypatch.setattr(cmd.LoginHandler, "_login", login)
    monkeypatch.setattr(cmd, "capture_web_session", capture)
    monkeypatch.setattr(cmd, "generate_oauth_url", lambda base, auth_type: {"auth_url": "https://login.microsoftonline.com/mobile", "code_verifier": "v"})
    monkeypatch.setattr(cmd, "exchange_code_for_tokens", exchange)


@pytest.mark.asyncio
async def test_a_refused_mobile_step_keeps_the_web_session(monkeypatch):
    patch(monkeypatch, cmd.LoginFailed("Login rejected"))
    result = await cmd.LoginHandler()._microsoft_login(BASE, cmd.LoginCommand(schulnetz_base_url=BASE, session_cookies=COOKIES))
    assert result.success
    assert result.access_token is None
    assert (result.session_id, result.web_session_user_id, result.web_session_trans_id) == ("php", "42", "t1")
    assert result.session_cookies


@pytest.mark.asyncio
async def test_both_steps_return_tokens_and_session(monkeypatch):
    patch(monkeypatch, None)
    result = await cmd.LoginHandler()._microsoft_login(BASE, cmd.LoginCommand(schulnetz_base_url=BASE, session_cookies=COOKIES))
    assert result.success and result.access_token == "access" and result.session_id == "php"
