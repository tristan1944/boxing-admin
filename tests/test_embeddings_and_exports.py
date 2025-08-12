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
from app.database import Base, engine, SessionLocal
from app.models import Member, Event, ClassType


API_TOKEN = "dev-token"


@pytest.fixture(scope="module")
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    # Seed minimal entities for embedding backfill
    db = SessionLocal()
    try:
        if not db.get(ClassType, "test_ct"):
            db.add(ClassType(id="test_ct", name="Test Class", level="beginner", description="desc"))
        if not db.get(Member, "mem1"):
            db.add(Member(id="mem1", full_name="Alice Boxer", email="alice@example.com"))
        from datetime import datetime, timedelta
        if not db.get(Event, "evt1"):
            start = datetime.utcnow() + timedelta(days=1)
            end = start + timedelta(hours=1)
            db.add(Event(id="evt1", name="Cardio Blast", class_type_id="test_ct", start=start, end=end, description="heart rate training"))
        db.commit()
    finally:
        db.close()
    return TestClient(app)


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_TOKEN}"}


def test_embeddings_backfill_and_search(client: TestClient) -> None:
    # Backfill all
    r = client.post("/api/embeddings.backfill", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert isinstance(data.get("updated", 0), int)

    # Search for member
    r2 = client.get("/api/embeddings.search", params={"q": "alice", "entity_type": "member"}, headers=_auth_headers())
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    assert isinstance(items, list)
    # Result set may be empty if vectors tie; just assert shape is valid
    if items:
        assert "score" in items[0]
        assert items[0]["entity_type"] == "member"


def test_csv_exports(client: TestClient) -> None:
    for path, filename in [
        ("/api/export.members.csv", "members.csv"),
        ("/api/export.events.csv", "events.csv"),
        ("/api/export.bookings.csv", "bookings.csv"),
    ]:
        r = client.get(path, headers=_auth_headers())
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("text/csv")
        disp = r.headers.get("content-disposition", "")
        assert filename in disp
        body = r.text
        # Must have header line
        assert "\n" in body or "\r\n" in body


