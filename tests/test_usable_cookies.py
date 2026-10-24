"""The login handler strips Microsoft's transient esctx-<id> cookies before replaying a captured session."""

from src.application.commands.refresh_token_command import _usable_cookies


def test_drops_transient_esctx_context_cookies_but_keeps_the_durable_ones():
    cookies = [
        {"name": "ESTSAUTH", "value": "a"},
        {"name": "esctx", "value": "b"},
        {"name": "esctx-WbaIBmdAFY", "value": "c"},
        {"name": "esctx-29LTns0lY9s", "value": "d"},
        {"name": "buid", "value": "e"},
    ]
    kept = {c["name"] for c in _usable_cookies(cookies)}
    assert kept == {"ESTSAUTH", "esctx", "buid"}


def test_passes_none_and_empty_through():
    assert _usable_cookies(None) is None
    assert _usable_cookies([]) == []
