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
from app.models import Payment, Refund, WhatsAppStatusEvent, MemberVisit


API_TOKEN = "dev-token"


def _auth_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_analytics_totals(client: TestClient) -> None:
    # Seed minimal rows
    db = SessionLocal()
    try:
        db.add(Payment(id="p_a", amount_cents=1000, currency="usd"))
        db.add(Refund(id="r_a", payment_id="p_a", amount_cents=200))
        db.add(WhatsAppStatusEvent(message_id="m1", status="delivered"))
        db.add(WhatsAppStatusEvent(message_id="m2", status="read"))
        db.add(MemberVisit(member_id="mem_x", event_id=None, source="test"))
        db.commit()
    finally:
        db.close()

    r = client.get("/api/analytics.totals", headers=_auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["payments"] >= 1
    assert data["refunds"] >= 1
    assert data["whatsapp_delivered"] >= 1
    assert data["whatsapp_read"] >= 1
    assert data["whatsapp_delivered_or_read"] >= data["whatsapp_delivered"]
    assert data["member_visits"] >= 1


