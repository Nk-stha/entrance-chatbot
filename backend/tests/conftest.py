import pytest
from fastapi.testclient import TestClient

from config import get_settings
from main import app


@pytest.fixture(scope="session")
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def admin_headers() -> dict[str, str]:
    return {"X-API-Key": get_settings().api_key}
