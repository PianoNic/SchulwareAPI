"""A TOTP code Microsoft already saw in this window is retried once with the next window's code."""

import pytest
from entrance import MfaRequired

from src.application.commands import refresh_token_command as cmd

URL = "https://login.microsoftonline.com/authorize"


def command(totp_secret="JBSWY3DPEHPK3PXP"):
    return cmd.LoginCommand(schulnetz_base_url="https://schulnetz.example.ch", email="a@b.ch", password="pw", totp_secret=totp_secret)


@pytest.fixture
def fake_login(monkeypatch):
    calls = {"login": 0, "slept": []}
    outcomes = []

    def login(*args, **kwargs):
        calls["login"] += 1
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def sleep(seconds):
        calls["slept"].append(seconds)

    monkeypatch.setattr(cmd, "ms_login", login)
    monkeypatch.setattr(cmd.asyncio, "sleep", sleep)
    return calls, outcomes


@pytest.mark.asyncio
async def test_a_duplicate_code_waits_for_the_next_window_and_retries(fake_login):
    calls, outcomes = fake_login
    outcomes += [MfaRequired("EndAuth/OTP rejected: PhoneAppOtpAuthFailedDuplicateCodeEntered"), {"code": "ok"}]
    assert await cmd.LoginHandler()._login(URL, command(), None) == {"code": "ok"}
    assert calls["login"] == 2
    assert len(calls["slept"]) == 1 and 1 <= calls["slept"][0] <= 31


@pytest.mark.asyncio
async def test_other_mfa_failures_are_not_retried(fake_login):
    calls, outcomes = fake_login
    outcomes += [MfaRequired("EndAuth/OTP rejected: OathCodeIncorrect")]
    with pytest.raises(MfaRequired):
        await cmd.LoginHandler()._login(URL, command(), None)
    assert calls["login"] == 1 and calls["slept"] == []


@pytest.mark.asyncio
async def test_without_a_secret_a_duplicate_code_is_not_retried(fake_login):
    calls, outcomes = fake_login
    outcomes += [MfaRequired("EndAuth/OTP rejected: PhoneAppOtpAuthFailedDuplicateCodeEntered")]
    with pytest.raises(MfaRequired):
        await cmd.LoginHandler()._login(URL, command(totp_secret=None), None)
    assert calls["login"] == 1


def test_next_window_is_one_second_past_the_boundary():
    assert cmd.seconds_to_next_totp_window(now=60.0) == 31
    assert cmd.seconds_to_next_totp_window(now=89.0) == 2
