"""OPENAPI_ENABLED and DOCS_ENABLED switch off /openapi.json and the docs page."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def restore_default_app(monkeypatch):
    yield
    monkeypatch.undo()
    from src.api import app as module
    importlib.reload(module)


def load(monkeypatch, **env):
    for name in ("OPENAPI_ENABLED", "DOCS_ENABLED"):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    from src.api import app as module
    return TestClient(importlib.reload(module).app)


@pytest.mark.parametrize("env, docs, openapi", [({}, 200, 200), ({"DOCS_ENABLED": "false"}, 404, 200), ({"OPENAPI_ENABLED": "false"}, 404, 404)])
def test_toggles(monkeypatch, env, docs, openapi):
    client = load(monkeypatch, **env)
    assert client.get("/").status_code == docs
    assert client.get("/openapi.json").status_code == openapi
