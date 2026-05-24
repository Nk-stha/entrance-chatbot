import json
from pathlib import Path

import pytest


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docs").exists():
            return parent
    pytest.skip("docs directory is not mounted in this test environment")


def test_api_contract_documents_required_endpoints_and_shapes() -> None:
    text = (repo_root() / "docs" / "api.md").read_text()
    required = [
        "POST /chat",
        "POST /chat/stream",
        "GET /admin/stats",
        "POST /admin/refresh",
        "POST /admin/sync",
        "POST /webhooks/sync",
        "GET /metrics",
        "CitationSource",
        "Session ID Handling",
        "Error Payload Shape",
    ]
    for item in required:
        assert item in text


def test_frontend_integration_documents_sse_events_and_cors() -> None:
    text = (repo_root() / "docs" / "frontend-integration.md").read_text()
    required = [
        "NEXT_PUBLIC_CHATBOT_API_BASE_URL",
        "streamChatMessage",
        "event === \"token\"",
        "event === \"sources\"",
        "event === \"done\"",
        "event === \"error\"",
        "event === \"heartbeat\"",
        "CORS_ORIGINS",
        "Do not create a new frontend app",
    ]
    for item in required:
        assert item in text


def test_postman_collection_is_valid_json_and_has_core_requests() -> None:
    collection = json.loads((repo_root() / "docs" / "postman_collection.json").read_text())
    names = {item["name"] for item in collection["item"]}
    assert {"Chat", "Chat Stream", "Admin Stats", "Webhook Sync", "Metrics"}.issubset(names)
