from fastapi.testclient import TestClient


def test_request_id_and_response_time_headers(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/health", headers={"X-Request-ID": "qa-request-1"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "qa-request-1"
    assert "X-Response-Time-MS" in response.headers


def test_admin_rejects_wrong_api_key(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/admin/stats", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["message"] == "Invalid admin API key"


def test_admin_accepts_configured_api_key(api_client: TestClient, admin_headers: dict[str, str], monkeypatch) -> None:
    from unittest.mock import Mock

    vector_store = Mock()
    vector_store.stats.return_value = {"collection": "entrance_knowledge", "count": 42}
    monkeypatch.setattr("api.admin.VectorStore", lambda: vector_store)

    response = api_client.get("/api/v1/admin/stats", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["collection"] == "entrance_knowledge"


def test_validation_error_is_sanitized(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/chat", json={"message": "", "session_id": "s1"})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"
    assert "input" not in str(body["error"].get("details", []))


def test_not_found_returns_consistent_error_shape(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/not-found")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "http_error"
