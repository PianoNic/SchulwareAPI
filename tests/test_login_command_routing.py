"""LoginHandler picks Schulnetz's own login or Microsoft, and falls back to Microsoft when the native attempt fails."""

import pytest

from src.application.commands import refresh_token_command as cmd
from src.application.dtos.refresh_dtos import LoginResponseDto

BASE = "https://schulnetz.example.ch"


def handler(monkeypatch, mode, native_ok, microsoft_ok):
    calls = []

    async def detect(base, user_agent=None):
        return mode

    async def native(self, base, command):
        calls.append("native")
        return LoginResponseDto(success=native_ok, message="native error" if not native_ok else None)

    async def microsoft(self, base, command):
        calls.append("microsoft")
        return LoginResponseDto(success=microsoft_ok, message="microsoft error" if not microsoft_ok else None)

    monkeypatch.setattr(cmd, "detect_login_mode", detect)
    monkeypatch.setattr(cmd.LoginHandler, "_native_login", native)
    monkeypatch.setattr(cmd.LoginHandler, "_microsoft_login", microsoft)
    return cmd.LoginHandler(), calls


def credentials():
    return cmd.LoginCommand(schulnetz_base_url=BASE, email="alex@school.ch", password="secret")


@pytest.mark.asyncio
async def test_a_microsoft_school_never_tries_the_native_form(monkeypatch):
    login, calls = handler(monkeypatch, "microsoft", True, True)
    assert (await login.handle(credentials())).success
    assert calls == ["microsoft"]


@pytest.mark.asyncio
async def test_a_native_school_signs_in_natively(monkeypatch):
    login, calls = handler(monkeypatch, "native", True, True)
    assert (await login.handle(credentials())).success
    assert calls == ["native"]


@pytest.mark.asyncio
async def test_a_failed_native_attempt_falls_back_to_microsoft(monkeypatch):
    login, calls = handler(monkeypatch, "native", False, True)
    assert (await login.handle(credentials())).success
    assert calls == ["native", "microsoft"]


@pytest.mark.asyncio
async def test_the_native_error_is_reported_when_both_fail(monkeypatch):
    login, _ = handler(monkeypatch, "native", False, False)
    result = await login.handle(credentials())
    assert not result.success
    assert result.message == "native error"


@pytest.mark.asyncio
async def test_a_cookie_only_reauth_skips_detection(monkeypatch):
    login, calls = handler(monkeypatch, "native", True, True)
    result = await login.handle(cmd.LoginCommand(schulnetz_base_url=BASE, session_cookies=[{"name": "x"}]))
    assert result.success
    assert calls == ["microsoft"]
