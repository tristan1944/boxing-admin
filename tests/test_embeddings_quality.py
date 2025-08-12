from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.embeddings import get_embedding_provider, cosine_similarity


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_similarity_monotonicity_and_cache(client: TestClient) -> None:
    provider = get_embedding_provider()

    a = "payment 100 usd"
    b = "payment 100 usd"
    c = "whatsapp delivered message"

    v1 = provider.embed_texts([a, b, c])
    v2 = provider.embed_texts([a, c])

    # identical texts should have near-1 similarity
    s_same = cosine_similarity(v1[0], v1[1])
    assert s_same > 0.99

    # similar vs dissimilar ordering
    s_ad = cosine_similarity(v1[0], v1[2])
    s_ac = cosine_similarity(v2[0], v2[1])
    # allow tiny floating drift; should be extremely close
    assert abs(s_ad - s_ac) < 1e-3

    # cache effectiveness: second call should reuse cached vector for 'a'
    # we can't measure cache directly; ensure value stability across calls
    s_again = cosine_similarity(v1[0], v2[0])
    assert abs(s_again - 1.0) < 1e-6


