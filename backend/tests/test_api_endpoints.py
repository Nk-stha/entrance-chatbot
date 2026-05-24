from datetime import datetime, timezone

from fastapi.testclient import TestClient

from config import get_settings
from main import app


client = TestClient(app)


def test_metrics_endpoint() -> None:
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "entrance_chatbot_up 1" in response.text


def test_admin_endpoints_reject_missing_api_key() -> None:
    assert client.post("/api/v1/admin/refresh").status_code == 401
    assert client.post("/api/v1/admin/sync", json={"source_type": "course"}).status_code == 401
    assert client.get("/api/v1/admin/stats").status_code == 401


def test_admin_stats_accepts_api_key() -> None:
    response = client.get("/api/v1/admin/stats", headers={"X-API-Key": get_settings().api_key})
    assert response.status_code == 200
    body = response.json()
    assert "collection" in body
    assert "count" in body


def test_webhook_requires_api_key() -> None:
    payload = {
        "event_id": "evt-test",
        "event_type": "refresh",
        "source_type": "course",
        "source_ids": ["course:8"],
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/api/v1/webhooks/sync", json=payload)
    assert response.status_code == 401


def test_chat_request_validation() -> None:
    response = client.post("/api/v1/chat", json={"message": "", "session_id": "s1"})
    assert response.status_code == 422


def test_openapi_contains_phase_13_routes() -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/chat" in paths
    assert "/api/v1/chat/stream" in paths
    assert "/api/v1/admin/refresh" in paths
    assert "/api/v1/admin/sync" in paths
    assert "/api/v1/admin/stats" in paths
    assert "/api/v1/webhooks/sync" in paths
    assert "/api/v1/metrics" in paths
