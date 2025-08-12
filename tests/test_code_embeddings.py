from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import pytest
from fastapi.testclient import TestClient

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.database import Base, engine


API_TOKEN = "dev-token"


@pytest.fixture(scope="module")
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_TOKEN}"}


def test_code_backfill_and_search(client: TestClient) -> None:
    params = {
        "root_dir": str(ROOT),
        "exts": ".py,.md",
        "ignores": "**/.venv/**,**/node_modules/**",
    }
    r = client.post("/api/code/backfill", params=params, headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("count"), int)
    assert isinstance(data.get("meta"), list)
    assert isinstance(data.get("vectors"), list)
    assert data["count"] == len(data["vectors"]) == len(data["meta"])  # shape integrity
    assert data["count"] >= 1

    r2 = client.post(
        "/api/code/search",
        params={"q": "booking capacity", **params, "limit": 5},
        headers=_auth_headers(),
    )
    assert r2.status_code == 200
    payload = r2.json()
    assert "items" in payload and "total" in payload
    if payload["items"]:
        first = payload["items"][0]
        assert "score" in first and "path" in first


