"""POST/DELETE /api/mobile/absences forward to Schulnetz me/absences and are in the OpenAPI schema."""

import httpx
import pytest
from fastapi.testclient import TestClient

from src.application.queries import proxy_mobile_rest_query as query_module

HEADERS = {"Authorization": "Bearer real-token", "X-Schulnetz-Base-Url": "https://schulnetz.bbbaden.ch"}


@pytest.fixture
def upstream(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "w5bA", "status": "0", "message": "Object successfully deleted"})
        return httpx.Response(200, json=[{"id": "w5bA", "status": "0", "message": "Absence created for profile X"}])

    real_client = httpx.AsyncClient
    monkeypatch.setattr(query_module.httpx, "AsyncClient", lambda *a, **k: real_client(transport=httpx.MockTransport(handler)))
    return seen


@pytest.fixture
def client():
    from src.api.app import app
    return TestClient(app)


def test_create_forwards_json_array(client, upstream):
    body = [{"studentId": "123", "dateFrom": "2026-11-07", "dateTo": "2026-11-07", "hourFrom": "08:00", "reason": "Arzt"}]
    response = client.post("/api/mobile/absences", json=body, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()[0]["id"] == "w5bA"
    request = upstream[0]
    assert request.method == "POST"
    assert str(request.url) == "https://schulnetz.bbbaden.ch/rest/v1/me/absences"
    assert request.headers["authorization"] == "Bearer real-token"
    import json
    assert json.loads(request.content) == body


def test_create_requires_mandatory_fields(client, upstream):
    response = client.post("/api/mobile/absences", json=[{"studentId": "123"}], headers=HEADERS)
    assert response.status_code == 422
    assert not upstream


def test_delete_forwards_to_absence_id(client, upstream):
    response = client.delete("/api/mobile/absences/w5bA", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "0"
    assert upstream[0].method == "DELETE"
    assert str(upstream[0].url) == "https://schulnetz.bbbaden.ch/rest/v1/me/absences/w5bA"


def test_openapi_lists_new_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "post" in paths["/api/mobile/absences"]
    assert "delete" in paths["/api/mobile/absences/{absence_id}"]


def test_user_info_keeps_permissions():
    from src.application.dtos.mobile.user_info_dto import UserInfoDto
    dto = UserInfoDto(**{"id": "1", "permissions": {"absences": ["abs_erfassen"]}})
    assert dto.model_dump()["permissions"]["absences"] == ["abs_erfassen"]
