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
from app.models import Payment
import uuid
from app.embeddings import get_embedding_provider, cosine_similarity


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_foundational_embeddings_for_db_entities(client: TestClient) -> None:
    # Insert a payment and compute a small vector representation of a textual summary
    db = SessionLocal()
    try:
        p = Payment(id=f"p_{uuid.uuid4().hex[:8]}", amount_cents=1234, currency="usd", description="Month of July")
        db.add(p)
        db.commit()
    finally:
        db.close()

    provider = get_embedding_provider()
    summary = f"payment {1234} cents currency usd description Month of July"
    vec = provider.embed_texts([summary])[0]
    # Sanity check: self similarity is ~1.0
    score = cosine_similarity(vec, vec)
    assert 0.99 <= score <= 1.01


