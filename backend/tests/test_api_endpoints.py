from datetime import datetime, timezone
from unittest.mock import Mock

from fastapi.testclient import TestClient


def test_metrics_endpoint(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "entrance_chatbot_up 1" in response.text


def test_admin_endpoints_reject_missing_api_key(api_client: TestClient) -> None:
    assert api_client.post("/api/v1/admin/refresh").status_code == 401
    assert api_client.post("/api/v1/admin/sync", json={"source_type": "course"}).status_code == 401
    assert api_client.get("/api/v1/admin/stats").status_code == 401


def test_admin_stats_accepts_api_key(api_client: TestClient, admin_headers: dict[str, str], monkeypatch) -> None:
    vector_store = Mock()
    vector_store.stats.return_value = {"collection": "entrance_knowledge", "count": 42}
    monkeypatch.setattr("api.admin.VectorStore", lambda: vector_store)

    response = api_client.get("/api/v1/admin/stats", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == {"collection": "entrance_knowledge", "count": 42}


def test_webhook_requires_api_key(api_client: TestClient) -> None:
    payload = {
        "event_id": "evt-test",
        "event_type": "refresh",
        "source_type": "course",
        "source_ids": ["course:8"],
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    response = api_client.post("/api/v1/webhooks/sync", json=payload)
    assert response.status_code == 401


def test_chat_request_validation(api_client: TestClient) -> None:
    response = api_client.post("/api/v1/chat", json={"message": "", "session_id": "s1"})
    assert response.status_code == 422


def test_openapi_contains_phase_13_routes(api_client: TestClient) -> None:
    schema = api_client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/chat" in paths
    assert "/api/v1/chat/stream" in paths
    assert "/api/v1/admin/refresh" in paths
    assert "/api/v1/admin/sync" in paths
    assert "/api/v1/admin/stats" in paths
    assert "/api/v1/webhooks/sync" in paths
    assert "/api/v1/metrics" in paths
