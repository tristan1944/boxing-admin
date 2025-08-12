from __future__ import annotations

import sys
from datetime import datetime, timedelta
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import Payment, Refund, WhatsAppMessage, WhatsAppStatusEvent
from sqlalchemy import delete
from app.analytics_math import compute_revenue_cents, compute_refund_rate, compute_whatsapp_delivery_rate


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Clean relevant tables to isolate tests
        db.execute(delete(Refund))
        db.execute(delete(Payment))
        db.execute(delete(WhatsAppStatusEvent))
        db.execute(delete(WhatsAppMessage))
        db.commit()
        yield db
    finally:
        db.close()


def test_revenue_and_refund_rate(db_session) -> None:
    anchor = datetime.utcnow() - timedelta(days=365)
    start = anchor
    end = anchor + timedelta(days=10)
    # 100 + 200 revenue, 50 refund (isolated window in the past)
    pid1 = f"p_{uuid.uuid4().hex[:8]}"
    pid2 = f"p_{uuid.uuid4().hex[:8]}"
    rid1 = f"r_{uuid.uuid4().hex[:8]}"
    db_session.add(Payment(id=pid1, created_at=anchor + timedelta(days=1), amount_cents=100))
    db_session.add(Payment(id=pid2, created_at=anchor + timedelta(days=2), amount_cents=200))
    db_session.add(Refund(id=rid1, created_at=anchor + timedelta(days=1), payment_id=pid1, amount_cents=50))
    db_session.commit()

    rev = compute_revenue_cents(db_session, start, end)
    rate = compute_refund_rate(db_session, start, end)
    assert rev == 250
    assert rate is not None and abs(rate - (50 / 300)) < 1e-6


def test_whatsapp_delivery_rate(db_session) -> None:
    anchor = datetime.utcnow() - timedelta(days=365)
    start = anchor
    end = anchor + timedelta(days=10)
    # Two messages, one delivered
    mid1 = f"m_{uuid.uuid4().hex[:8]}"
    mid2 = f"m_{uuid.uuid4().hex[:8]}"
    db_session.add(WhatsAppMessage(id=mid1, created_at=anchor + timedelta(days=1), group_id="g", content="hi", status="queued"))
    db_session.add(WhatsAppMessage(id=mid2, created_at=anchor + timedelta(days=1), group_id="g", content="hi2", status="queued"))
    db_session.add(WhatsAppStatusEvent(message_id=mid1, status="delivered", created_at=anchor + timedelta(days=2)))
    db_session.commit()

    rate = compute_whatsapp_delivery_rate(db_session, start, end)
    assert rate is not None and abs(rate - 0.5) < 1e-6


