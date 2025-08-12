from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_health_and_auth_smoke(client: TestClient) -> None:
    # health open
    hr = client.get("/health")
    assert hr.status_code == 200
    # basic unauthorized check (endpoint exists, returns 401)
    r = client.get("/api/members.list")
    assert r.status_code == 401


