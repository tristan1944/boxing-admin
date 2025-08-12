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
from app.models import CodeEmbedding


API_TOKEN = "dev-token"


def _auth_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


@pytest.fixture()
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def test_persisted_code_embeddings_mapping_fields(client: TestClient) -> None:
    r = client.post(
        "/api/code/backfill",
        params={"root_dir": str(ROOT / "app"), "exts": ".py", "persist": True},
        headers=_auth_headers(),
    )
    assert r.status_code == 200

    db = SessionLocal()
    try:
        rows = db.query(CodeEmbedding).all()
        assert len(rows) >= 1
        for row in rows:
            assert isinstance(row.chunk_idx, int)
            assert row.chunk_idx >= 0
            assert row.path and row.path.endswith(".py")
            assert row.file_sha256 and len(row.file_sha256) == 64
            assert row.text_hash and len(row.text_hash) == 64
            # lang derived from extension
            assert row.lang in {"py"}
            assert row.vector is not None and isinstance(row.vector, list)
    finally:
        db.close()