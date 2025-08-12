from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


API_TOKEN = "dev-token"


def _auth_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_code_persist_and_search(client: TestClient) -> None:
    # Persist embeddings for .py files under app/
    r = client.post(
        "/api/code/backfill",
        params={"root_dir": str(ROOT / "app"), "exts": ".py", "ignores": "**/.venv/**", "persist": True},
        headers=_auth_headers(),
    )
    assert r.status_code == 200
    assert r.json().get("persisted") is True

    # Search persisted
    r2 = client.post(
        "/api/code/search",
        params={"q": "analytics math", "use_persisted": True},
        headers=_auth_headers(),
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("source") == "persisted"
    assert data.get("total", 0) >= 1


