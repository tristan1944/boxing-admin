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


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_payments_and_refunds_flow(client: TestClient) -> None:
    # Create payment
    r = client.post(
        "/api/payments.create",
        json={"amount_cents": 2500, "currency": "usd", "description": "Monthly"},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.text
    pay = r.json()
    assert pay["amount_cents"] == 2500

    # Partial refund
    r2 = client.post(
        "/api/refunds.create",
        json={"payment_id": pay["id"], "amount_cents": 1000, "reason": "goodwill"},
        headers=_auth_headers(),
    )
    assert r2.status_code == 200, r2.text
    ref = r2.json()
    assert ref["amount_cents"] == 1000

    # Over-refund should fail
    r3 = client.post(
        "/api/refunds.create",
        json={"payment_id": pay["id"], "amount_cents": 2000},
        headers=_auth_headers(),
    )
    assert r3.status_code == 400

    # List payments
    r4 = client.get("/api/payments.list", headers=_auth_headers())
    assert r4.status_code == 200
    assert r4.json()["total"] >= 1

    # List refunds by payment
    r5 = client.get("/api/refunds.list", params={"payment_id": pay["id"]}, headers=_auth_headers())
    assert r5.status_code == 200
    assert r5.json()["total"] >= 1


