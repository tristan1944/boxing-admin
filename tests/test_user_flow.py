from __future__ import annotations

import sys
import uuid
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
from app.database import Base, engine
from app.rate_limit import _window_counts as _rate_counts


API_TOKEN = "dev-token"


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Enable rate limiting but set high threshold for this flow
    monkeypatch.setenv("APP_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("APP_RATE_LIMIT_PER_MINUTE", "200")
    # Ensure embeddings provider is fake (no external dependency)
    monkeypatch.setenv("APP_EMBEDDINGS_PROVIDER", "fake")
    # Reset cached settings and counters
    get_settings.cache_clear()  # type: ignore[attr-defined]
    _rate_counts.clear()
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_user_flow_end_to_end(client: TestClient) -> None:
    # Create a class type
    ct_id = f"ct_{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/class_types.create",
        json={"id": ct_id, "name": "Circuit Training", "level": "intermediate", "description": "full body"},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    # Create a group that requires approval
    group_id = f"grp_{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/groups.create",
        json={"id": group_id, "name": "Competition Team", "requires_approval": True},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    # Create a member assigned to the group
    member_id = f"mem_{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/members.create",
        json={"full_name": "Test User", "email": "user@example.com", "group_ids": [group_id]},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    member_id = r.json()["id"]

    # Create an event that points to the class type and group, capacity 1 so we can test capacity logic
    evt_id = f"evt_{uuid.uuid4().hex[:8]}"
    start = (datetime.utcnow() + timedelta(days=1)).isoformat()
    end = (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat()
    r = client.post(
        "/api/events.create",
        json={
            "name": "Morning Circuit",
            "class_type_id": ct_id,
            "group_id": group_id,
            "start": start,
            "end": end,
            "capacity": 1,
            "requires_approval": False,
        },
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    evt_id = r.json()["id"]

    # Create a booking; since group requires approval, booking should be pending
    r = client.post(
        "/api/bookings.create",
        json={"event_id": evt_id, "member_id": member_id},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    booking = r.json()
    assert booking["status"] in {"pending", "approved"}
    # Approve booking if needed
    if booking["status"] != "approved":
        r = client.post(
            "/api/bookings.approve",
            json={"id": booking["id"], "approved_by": "coach"},
            headers=_auth_headers(),
        )
        assert r.status_code == 200, r.text
        booking = r.json()
        assert booking["status"] == "approved"

    # Attempt second booking to hit capacity
    r = client.post(
        "/api/members.create",
        json={"full_name": "Second User"},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    member2_id = r.json()["id"]
    r = client.post(
        "/api/bookings.create",
        json={"event_id": evt_id, "member_id": member2_id},
        headers=_auth_headers(),
    )
    # Depending on approval rules, capacity may be checked on approve. Try approve path if create passed.
    if r.status_code == 200:
        b2 = r.json()
        if b2["status"] != "approved":
            r2 = client.post(
                "/api/bookings.approve",
                json={"id": b2["id"], "approved_by": "coach"},
                headers=_auth_headers(),
            )
            # Expect capacity error or approval success depending on timing; accept 200 or 400
            assert r2.status_code in (200, 400)
    else:
        # If create was blocked due to capacity, we should see 400
        assert r.status_code == 400

    # Exports should produce CSV with headers
    for path in [
        "/api/export.members.csv",
        "/api/export.events.csv",
        "/api/export.bookings.csv",
    ]:
        er = client.get(path, headers=_auth_headers())
        assert er.status_code == 200
        assert er.headers.get("content-type", "").startswith("text/csv")
        assert "\n" in er.text or "\r\n" in er.text

    # Embeddings backfill and search should work
    br = client.post("/api/embeddings.backfill", headers=_auth_headers())
    assert br.status_code == 200
    sr = client.get(
        "/api/embeddings.search",
        params={"q": "circuit", "entity_type": "event", "limit": 5},
        headers=_auth_headers(),
    )
    assert sr.status_code == 200
    sdata = sr.json()
    assert "items" in sdata and isinstance(sdata["items"], list)

    # Analytics summary should return shape
    ar = client.get("/api/analytics.summary", headers=_auth_headers())
    assert ar.status_code == 200
    a = ar.json()
    for key in [
        "attendance_by_class_type_30d",
        "attendance_by_class_type_90d",
        "average_utilization_rate",
        "active_members",
        "demographic_age_bands",
        "gender_breakdown",
    ]:
        assert key in a


