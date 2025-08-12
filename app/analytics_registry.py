from __future__ import annotations

"""
EMBED_SUMMARY: Structured registry of analytics metrics (facts, KPIs, windowed) with SQL sketches and dependencies.
EMBED_TAGS: analytics, registry, metrics, facts, kpis, windowed, sql, documentation

Each metric here complements docstring anchors in code and optional DB views. The registry
provides a canonical description and metadata for testing and for the future calculator mapping.

Fields:
- name: Unique metric identifier (e.g., payments.count)
- category: fact | kpi | windowed
- inputs: list of source tables/columns referenced
- dependencies: other metric names this metric depends on (for KPIs/windowed)
- sql_sketch: representative SQL (portable, SQLite-first) describing how to compute
- constraints: list of textual constraints (NULL-handling, domain)
- description: human summary
- tags: keywords
- test_ids: IDs or names of tests that assert behavior/shape
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


MetricCategory = Literal["fact", "kpi", "windowed"]


class Metric(BaseModel):
    name: str
    category: MetricCategory
    inputs: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    sql_sketch: str
    constraints: List[str] = Field(default_factory=list)
    description: str
    tags: List[str] = Field(default_factory=list)
    test_ids: List[str] = Field(default_factory=list)


# Initial registry entries anchored to current implementation and tests
metrics: List[Metric] = [
    Metric(
        name="payments.count",
        category="fact",
        inputs=["payments"],
        sql_sketch="SELECT COUNT(*) FROM payments;",
        constraints=["non-negative integer"],
        description="Total number of payment records.",
        tags=["payments", "facts"],
        test_ids=["test_analytics_totals"],
    ),
    Metric(
        name="payments.gross_amount_cents",
        category="fact",
        inputs=["payments.amount_cents"],
        sql_sketch="SELECT COALESCE(SUM(amount_cents),0) FROM payments;",
        constraints=["non-negative integer", "NULL-safe sum"],
        description="Sum of all payment amounts in cents.",
        tags=["payments", "facts", "revenue"],
        test_ids=["test_analytics_facts"],
    ),
    Metric(
        name="payments.avg_amount_cents",
        category="fact",
        inputs=["payments.amount_cents"],
        sql_sketch="SELECT COALESCE(AVG(amount_cents),0.0) FROM payments;",
        constraints=["float", "NULL-safe avg"],
        description="Average payment amount in cents.",
        tags=["payments", "facts"],
        test_ids=["test_analytics_facts"],
    ),
    Metric(
        name="refunds.count",
        category="fact",
        inputs=["refunds"],
        sql_sketch="SELECT COUNT(*) FROM refunds;",
        constraints=["non-negative integer"],
        description="Total number of refund records.",
        tags=["refunds", "facts"],
        test_ids=["test_analytics_totals"],
    ),
    Metric(
        name="refunds.gross_amount_cents",
        category="fact",
        inputs=["refunds.amount_cents"],
        sql_sketch="SELECT COALESCE(SUM(amount_cents),0) FROM refunds;",
        constraints=["non-negative integer", "NULL-safe sum"],
        description="Sum of refund amounts in cents.",
        tags=["refunds", "facts"],
        test_ids=["test_analytics_facts"],
    ),
    Metric(
        name="whatsapp.error_count",
        category="fact",
        inputs=["whatsapp_status_events.status"],
        sql_sketch="SELECT COUNT(*) FROM whatsapp_status_events WHERE status='error';",
        constraints=["non-negative integer"],
        description="Count of WhatsApp error status events.",
        tags=["whatsapp", "facts", "delivery"],
        test_ids=["test_analytics_totals"],
    ),
    Metric(
        name="kpi.payments_success_rate",
        category="kpi",
        inputs=["payments.status"],
        dependencies=["payments.count"],
        sql_sketch=(
            "SELECT CASE WHEN COUNT(*)<=0 THEN NULL ELSE "
            "CAST(SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) AS FLOAT) / CAST(COUNT(*) AS FLOAT) END FROM payments;"
        ),
        constraints=["NULL if denominator is zero", "0..1 range when not NULL"],
        description="Share of payments that succeeded.",
        tags=["payments", "kpi"],
        test_ids=["test_analytics_kpis_present"],
    ),
    Metric(
        name="kpi.whatsapp_error_rate",
        category="kpi",
        inputs=["whatsapp_status_events.status"],
        dependencies=[],
        sql_sketch=(
            "SELECT CASE WHEN COUNT(*)<=0 THEN NULL ELSE "
            "CAST(SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) AS FLOAT)/CAST(COUNT(*) AS FLOAT) END FROM whatsapp_status_events;"
        ),
        constraints=["NULL if denominator is zero", "0..1 range when not NULL"],
        description="Share of WhatsApp status events that are errors.",
        tags=["whatsapp", "kpi"],
        test_ids=["test_analytics_kpis_present"],
    ),
    Metric(
        name="windowed.revenue_cents",
        category="windowed",
        inputs=["payments.amount_cents", "refunds.amount_cents"],
        dependencies=[],
        sql_sketch=(
            "WITH p AS (SELECT COALESCE(SUM(amount_cents),0) AS s FROM payments WHERE created_at BETWEEN :start AND :end), "
            "r AS (SELECT COALESCE(SUM(amount_cents),0) AS s FROM refunds WHERE created_at BETWEEN :start AND :end) "
            "SELECT p.s - r.s AS revenue_cents FROM p, r;"
        ),
        constraints=["integer", "window inclusive of bounds"],
        description="Revenue in cents over a time window.",
        tags=["payments", "refunds", "windowed", "revenue"],
        test_ids=["test_revenue_and_refund_rate"],
    ),
]


def get_metric(name: str) -> Optional[Metric]:
    for m in metrics:
        if m.name == name:
            return m
    return None