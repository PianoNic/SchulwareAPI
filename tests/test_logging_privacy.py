import logging
import runpy
from unittest import mock

import uvicorn

from src.infrastructure.logging_config import setup_colored_logging


def test_access_log_is_off():
    with mock.patch.object(uvicorn, "run") as run:
        runpy.run_path("asgi.py", run_name="__main__")
    assert run.call_args.kwargs["access_log"] is False


def test_request_urls_are_not_logged_by_httpx():
    setup_colored_logging()
    assert not logging.getLogger("httpx").isEnabledFor(logging.INFO)
    assert not logging.getLogger("httpcore").isEnabledFor(logging.INFO)
