from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.analytics_registry import metrics, get_metric, Metric


def test_registry_presence_and_shape() -> None:
    assert isinstance(metrics, list) and len(metrics) >= 1
    # required fields present and non-empty for a few known metrics
    names = {m.name for m in metrics}
    for required in [
        "payments.count",
        "payments.gross_amount_cents",
        "refunds.count",
        "kpi.payments_success_rate",
        "windowed.revenue_cents",
    ]:
        assert required in names
    # check shape
    for m in metrics:
        assert isinstance(m.name, str) and m.name
        assert m.category in ("fact", "kpi", "windowed")
        assert isinstance(m.sql_sketch, str) and m.sql_sketch.strip()
        assert isinstance(m.description, str) and m.description.strip()
        assert isinstance(m.inputs, list)
        assert isinstance(m.constraints, list)


def test_registry_lookup() -> None:
    m = get_metric("payments.count")
    assert m is not None and isinstance(m, Metric)
    assert "COUNT" in m.sql_sketch.upper()