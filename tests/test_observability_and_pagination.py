from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

import pytest
from fastapi.testclient import TestClient

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.config import get_settings
from app.database import Base, engine, SessionLocal
from app.models import ClassType, Group, Member, Event
from app.rate_limit import _window_counts as _rate_counts


API_TOKEN = "dev-token"


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Fast provider, RL on but high
    monkeypatch.setenv("APP_EMBEDDINGS_PROVIDER", "fake")
    monkeypatch.setenv("APP_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("APP_RATE_LIMIT_PER_MINUTE", "200")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    _rate_counts.clear()
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_observability_headers_and_errors(client: TestClient) -> None:
    # Successful response should include timing header
    r = client.get("/health")
    assert r.status_code == 200
    assert "X-Process-Time-Ms" in r.headers

    # Error payload should follow shape
    r2 = client.get("/api/members.list")  # missing token
    assert r2.status_code == 401
    data = r2.json()
    assert data.get("ok") is False
    assert "error" in data and "status" in data["error"] and "path" in data["error"]


def _seed_members_groups_events(db):
    # Create groups
    for i in range(3):
        gid = f"g{i}"
        if not db.get(Group, gid):
            db.add(Group(id=gid, name=f"Group {i}", requires_approval=False))
    # Create class types
    for i in range(3):
        cid = f"ct{i}"
        if not db.get(ClassType, cid):
            db.add(ClassType(id=cid, name=f"Class {i}", level="beginner"))
    db.commit()

    # Create members spread across groups and sources
    for i in range(30):
        mid = f"m{i}"
        if not db.get(Member, mid):
            m = Member(id=mid, full_name=f"Member {i}", email=f"m{i}@ex.com", status="active" if i % 2 == 0 else "paused", source="ad" if i % 3 == 0 else "ref")
            if i % 2 == 0:
                m.groups = [db.get(Group, "g0")]  # type: ignore[arg-type]
            db.add(m)
    db.commit()

    # Events for pagination and filters
    now = datetime.utcnow()
    for i in range(12):
        eid = f"e{i}"
        if not db.get(Event, eid):
            db.add(
                Event(
                    id=eid,
                    name=f"Event {i}",
                    class_type_id="ct0",
                    start=now + timedelta(days=i),
                    end=now + timedelta(days=i, hours=1),
                    is_special=(i % 2 == 0),
                )
            )
    db.commit()


def test_pagination_and_filters(client: TestClient) -> None:
    # Seed using a DB session directly
    db = SessionLocal()
    try:
        _seed_members_groups_events(db)
    finally:
        db.close()

    # Pagination: page=2 of members with page_size=5
    r = client.get("/api/members.list", params={"page": 2, "page_size": 5}, headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 10
    assert len(data["items"]) == 5

    # Filter by status
    r2 = client.get("/api/members.list", params={"status": "active"}, headers=_auth_headers())
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["total"] > 0

    # Filter by source
    r3 = client.get("/api/members.list", params={"source": "ad"}, headers=_auth_headers())
    assert r3.status_code == 200
    data3 = r3.json()
    assert data3["total"] > 0

    # Events filter by is_special and pagination
    r4 = client.get("/api/events.list", params={"is_special": True, "page": 1, "page_size": 3}, headers=_auth_headers())
    assert r4.status_code == 200
    data4 = r4.json()
    assert len(data4["items"]) <= 3


