"""Browser sign-in: start hands out a state, verifier and device id; complete and refresh pass the device id on."""

import pytest

from src.application.commands import browser_login_command as browser


@pytest.mark.asyncio
async def test_start_returns_an_authorize_url_with_its_state():
    start = await browser.StartBrowserLoginHandler().handle(browser.StartBrowserLoginCommand(schulnetz_base_url="https://schulnetz.example.ch/"))
    assert start.auth_url.startswith("https://schulnetz.example.ch/authorize.php?")
    assert f"state={start.state}" in start.auth_url
    assert start.callback_url == "https://schulnetz.web.app/callback"
    assert start.code_verifier and start.device_id


@pytest.mark.asyncio
async def test_complete_exchanges_the_code_with_the_device_id(monkeypatch):
    seen = {}

    async def exchange(code, verifier, base, device_id=None):
        seen.update(code=code, verifier=verifier, base=base, device_id=device_id)
        return "access", "refresh"

    monkeypatch.setattr(browser, "exchange_code_for_tokens", exchange)
    result = await browser.CompleteBrowserLoginHandler().handle(browser.CompleteBrowserLoginCommand(schulnetz_base_url="https://schulnetz.example.ch/", code="c0de", code_verifier="v", device_id="d"))
    assert result.success and result.access_token == "access" and result.refresh_token == "refresh"
    assert seen == {"code": "c0de", "verifier": "v", "base": "https://schulnetz.example.ch", "device_id": "d"}


@pytest.mark.asyncio
async def test_refresh_reports_a_refusal(monkeypatch):
    async def refresh(token, device_id, base):
        return None, None, "biometric_required"

    monkeypatch.setattr(browser, "refresh_mobile_tokens", refresh)
    result = await browser.RefreshMobileTokenHandler().handle(browser.RefreshMobileTokenCommand(schulnetz_base_url="https://schulnetz.example.ch", refresh_token="r", device_id="d"))
    assert not result.success and "biometric_required" in result.message
