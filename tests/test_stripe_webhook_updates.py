from __future__ import annotations

import sys
from pathlib import Path
import json

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Payment, Refund


API_TOKEN = "dev-token"


def _auth_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_stripe_payment_intent_and_charge_refund(client: TestClient) -> None:
    # payment_intent.succeeded → create/update payment
    intent_payload = {
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_123", "amount_received": 2000, "currency": "usd"}},
    }
    r1 = client.post(
        "/api/stripe.webhook",
        data=json.dumps(intent_payload),
        headers={**_auth_headers(), "Content-Type": "application/json"},
    )
    assert r1.status_code == 200

    # charge.refunded → create refund and update payment
    charge_payload = {
        "type": "charge.refunded",
        "data": {
            "object": {
                "id": "ch_1",
                "amount": 2000,
                "currency": "usd",
                "amount_refunded": 500,
                "refunds": {"data": [{"id": "re_1", "amount": 500}]},
            }
        },
    }
    r2 = client.post(
        "/api/stripe.webhook",
        data=json.dumps(charge_payload),
        headers={**_auth_headers(), "Content-Type": "application/json"},
    )
    assert r2.status_code == 200

    db = SessionLocal()
    try:
        pays = db.query(Payment).all()
        assert len(pays) >= 1
        # ensure refunded amount persisted
        p = db.query(Payment).filter(Payment.provider_charge_id == "ch_1").first()
        assert p is not None
        assert p.refunded_amount_cents >= 500
        refs = db.query(Refund).filter(Refund.payment_id == p.id).all()
        assert any(r.amount_cents == 500 for r in refs)
    finally:
        db.close()


