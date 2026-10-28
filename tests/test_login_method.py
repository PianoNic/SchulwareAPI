"""DetectLoginMethodQuery reports the school's sign-in from detect_login_mode."""

import pytest

from src.application.queries import detect_login_method_query as query


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["microsoft", "native", "browser"])
async def test_reports_the_detected_method(monkeypatch, mode):
    seen = {}

    async def detect(base_url, user_agent=None):
        seen["base_url"] = base_url
        return mode

    monkeypatch.setattr(query, "detect_login_mode", detect)
    result = await query.DetectLoginMethodHandler().handle(query.DetectLoginMethodQuery(base_url="https://schulnetz.example.ch/"))
    assert result.method == mode
    assert seen["base_url"] == "https://schulnetz.example.ch"
