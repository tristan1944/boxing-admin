from __future__ import annotations

import os
from typing import Dict
import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.rate_limit import _window_counts as _rate_counts
from app.database import Base, engine


API_TOKEN = os.getenv("APP_API_TOKEN", "dev-token")


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Ensure schema exists when tests run standalone
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_TOKEN}"}


def test_health_open(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_auth_required_on_api(client: TestClient) -> None:
    r = client.get("/api/campaigns.list")
    assert r.status_code == 401


def test_campaigns_list_authorized(client: TestClient) -> None:
    r = client.get("/api/campaigns.list", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_rate_limit_toggle(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure rate limit disabled by default (per settings)
    r = client.get("/api/campaigns.list", headers=_auth_headers())
    assert r.status_code == 200

    # Enable rate limit and set low threshold
    monkeypatch.setenv("APP_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("APP_RATE_LIMIT_PER_MINUTE", "3")
    # Reset cached settings and counters
    get_settings.cache_clear()  # type: ignore[attr-defined]
    _rate_counts.clear()

    # First 3 pass
    for _ in range(3):
        ok = client.get("/api/campaigns.list", headers=_auth_headers())
        assert ok.status_code == 200
    # 4th should hit 429
    blocked = client.get("/api/campaigns.list", headers=_auth_headers())
    assert blocked.status_code == 429


