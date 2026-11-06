import logging

from entrance import LoginFailed, NeedsCredentials

from src.application.commands.refresh_token_command import _log_failure


def _logged(caplog, ex):
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        _log_failure("mobile", ex)
    return caplog.records[-1].getMessage()


def test_takes_the_number_from_an_oauth_error(caplog):
    line = _logged(caplog, LoginFailed("OAuth error: AADSTS65001: The user someone@school.ch has not consented"))
    assert line == "Microsoft login failed at the mobile step: LoginFailed, oauth (AADSTS 65001)"
    assert "someone" not in line


def test_takes_the_number_from_an_entra_error(caplog):
    assert _logged(caplog, LoginFailed("Entra error sErrorCode=50076: text")).endswith("entra (AADSTS 50076)")


def test_names_the_kind_without_a_number(caplog):
    assert _logged(caplog, LoginFailed("Too many hops without reaching the callback code.")).endswith("hops (AADSTS -)")
    assert _logged(caplog, NeedsCredentials()).endswith("NeedsCredentials, - (AADSTS -)")
