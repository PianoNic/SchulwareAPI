import pytest
from src.application.services.schulnetz_credential_scraper import get_credentials

@pytest.mark.asyncio
async def test_get_credentials():
    result = await get_credentials("https://example.schulnetz.ch")
    assert result == "hello"
