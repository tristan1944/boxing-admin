from __future__ import annotations

import sys
from pathlib import Path
import uuid

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import WhatsAppMessage, WhatsAppStatusEvent


API_TOKEN = "dev-token"


def _auth_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_whatsapp_status_variant_payloads(client: TestClient) -> None:
    # Seed a message
    msg_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(WhatsAppMessage(id=msg_id, group_id="g1", content="Hi", status="queued"))
        db.commit()
    finally:
        db.close()

    # Alternate shape: {messageId, state, errorCode}
    r1 = client.post(
        "/api/whatsapp.status",
        json={"messageId": msg_id, "state": "sent"},
        headers=_auth_headers(),
    )
    assert r1.status_code == 200

    # Alias mapping: seen -> read
    r2 = client.post(
        "/api/whatsapp.status",
        json={"messageId": msg_id, "state": "seen"},
        headers=_auth_headers(),
    )
    assert r2.status_code == 200

    # Failure alias
    r3 = client.post(
        "/api/whatsapp.status",
        json={"messageId": msg_id, "state": "failed", "errorCode": "X"},
        headers=_auth_headers(),
    )
    assert r3.status_code == 200

    # Verify
    db2 = SessionLocal()
    try:
        events = db2.query(WhatsAppStatusEvent).filter(WhatsAppStatusEvent.message_id == msg_id).all()
        assert len(events) == 3
        states = {e.status for e in events}
        assert states == {"delivered", "read", "error"}
    finally:
        db2.close()