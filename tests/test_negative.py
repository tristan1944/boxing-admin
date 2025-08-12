from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict
import uuid

import pytest
from fastapi.testclient import TestClient

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.database import Base, engine, SessionLocal
from app.config import get_settings
from app.rate_limit import _window_counts as _rate_counts


API_TOKEN = "dev-token"


def _auth_headers(token: str = API_TOKEN) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Keep RL enabled but high to avoid interference unless explicitly tested
    monkeypatch.setenv("APP_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("APP_RATE_LIMIT_PER_MINUTE", "200")
    monkeypatch.setenv("APP_EMBEDDINGS_PROVIDER", "fake")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    _rate_counts.clear()
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_invalid_token_401(client: TestClient) -> None:
    r = client.get("/api/members.list", headers=_auth_headers("bad-token"))
    assert r.status_code == 401


def test_events_create_invalid_fk_400(client: TestClient) -> None:
    from datetime import datetime, timedelta

    start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end = (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat()
    r = client.post(
        "/api/events.create",
        json={
            "name": "Bad Event",
            "class_type_id": "does_not_exist",
            "start": start,
            "end": end,
        },
        headers=_auth_headers(),
    )
    assert r.status_code == 400


def test_members_update_not_found_404(client: TestClient) -> None:
    r = client.post(
        "/api/members.update",
        json={"id": "missing", "full_name": "x"},
        headers=_auth_headers(),
    )
    assert r.status_code == 404


def test_groups_and_class_types_duplicates_400(client: TestClient) -> None:
    # Create once
    gid = f"dupgrp_{uuid.uuid4().hex[:8]}"
    r1 = client.post(
        "/api/groups.create", json={"id": gid, "name": "Dup"}, headers=_auth_headers()
    )
    assert r1.status_code == 200
    # Duplicate
    r2 = client.post(
        "/api/groups.create", json={"id": gid, "name": "Dup"}, headers=_auth_headers()
    )
    assert r2.status_code == 400

    # ClassType
    cid = f"dupct_{uuid.uuid4().hex[:8]}"
    r3 = client.post(
        "/api/class_types.create", json={"id": cid, "name": "Dup CT"}, headers=_auth_headers()
    )
    assert r3.status_code == 200
    r4 = client.post(
        "/api/class_types.create", json={"id": cid, "name": "Dup CT"}, headers=_auth_headers()
    )
    assert r4.status_code == 400


def test_bookings_invalid_refs_and_not_found(client: TestClient) -> None:
    # invalid refs on create
    r = client.post(
        "/api/bookings.create",
        json={"event_id": "nope", "member_id": "nope"},
        headers=_auth_headers(),
    )
    assert r.status_code == 400

    # approve/cancel not found
    r2 = client.post(
        "/api/bookings.approve", json={"id": "nope", "approved_by": "coach"}, headers=_auth_headers()
    )
    assert r2.status_code == 404
    r3 = client.post(
        "/api/bookings.cancel", json={"id": "nope"}, headers=_auth_headers()
    )
    assert r3.status_code == 404


def test_embeddings_backfill_invalid_entity_type_400(client: TestClient) -> None:
    r = client.post(
        "/api/embeddings.backfill", params={"entity_type": "unknown"}, headers=_auth_headers()
    )
    assert r.status_code == 400


def test_qr_checkin_invalids(client: TestClient) -> None:
    # Invalid token
    r = client.get("/checkin", params={"token": "bad", "member_id": "x"})
    assert r.status_code == 401
    # Valid token but missing member
    from app.config import get_settings as _gs

    token = _gs().qr_token
    r2 = client.get("/checkin", params={"token": token, "member_id": "missing"})
    assert r2.status_code == 404


def test_devtools_missing_package_json(client: TestClient, tmp_path: Path) -> None:
    r = client.get(
        "/api/dev/npm.dedupe-plan", params={"project_root": str(tmp_path)}, headers=_auth_headers()
    )
    assert r.status_code == 404


def test_code_search_no_files(client: TestClient, tmp_path: Path) -> None:
    # Create empty directory
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    r = client.post(
        "/api/code/search",
        params={"q": "anything", "root_dir": str(empty_dir), "exts": ".py"},
        headers=_auth_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("total") == 0
    assert data.get("items") == []


