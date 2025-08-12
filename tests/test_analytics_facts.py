from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Member, Event, Booking, ClassType, Group, FacebookCampaign


API_TOKEN = "dev-token"


def _auth_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_analytics_summary_includes_facts(client: TestClient) -> None:
    # Seed minimal related data to exercise counts
    db = SessionLocal()
    try:
        if not db.get(ClassType, "ctA"):
            db.add(ClassType(id="ctA", name="A"))
        if not db.get(Group, "gA"):
            db.add(Group(id="gA", name="G"))
        if not db.get(FacebookCampaign, "fbA"):
            db.add(FacebookCampaign(id="fbA", name="C"))
        db.commit()
    finally:
        db.close()

    r = client.get("/api/analytics.totals", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert "payments" in data and "refunds" in data and "whatsapp_delivered_or_read" in data


