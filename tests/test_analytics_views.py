from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.database import Base, engine, SessionLocal


API_TOKEN = "dev-token"


def _auth_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    # lifespan should create views, but ensure explicitly
    from app.sql_views import create_views
    create_views(engine)
    return TestClient(app)


def test_foundational_views_exist_and_shape(client: TestClient) -> None:
    db = SessionLocal()
    try:
        # payments facts view should exist with 3 columns
        rows = db.execute(text("SELECT payments_count, payments_gross_amount_cents, payments_avg_amount_cents FROM vw_payments_facts")).all()
        assert len(rows) == 1
        cnt, gross, avg = rows[0]
        assert isinstance(cnt, int)
        assert isinstance(gross, int)
        assert isinstance(avg, float)

        # whatsapp facts view should exist with delivered/read/error/total
        rows2 = db.execute(text("SELECT delivered, read, error, total FROM vw_whatsapp_facts")).all()
        assert len(rows2) == 1
        d, r, e, t = rows2[0]
        assert d + r + e <= t
    finally:
        db.close()