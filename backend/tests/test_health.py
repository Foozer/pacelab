"""Health endpoint tests. PostgreSQL must be reachable via DATABASE_URL."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok_when_database_is_up(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"
    assert payload["version"]
    assert payload["environment"] == "test"


def test_health_sets_security_headers(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_unknown_route_uses_structured_error(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "NOT_FOUND"
    assert "message" in payload["error"]


def test_openapi_available_outside_production(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "PaceLab API"
