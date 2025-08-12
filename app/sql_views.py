from __future__ import annotations

"""
EMBED_SUMMARY: SQL view definitions for stable facts/KPIs to support analytics without time bucketing.
EMBED_TAGS: analytics, sql, views, facts, kpis

This module maintains CREATE VIEW statements for SQLite (portable subset). Views are optional
and primarily serve as anchors alongside code and the analytics registry.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def create_views(engine: Engine) -> None:
    """Create or replace foundational analytics views. Idempotent for SQLite.

    Views:
    - vw_payments_facts: count, gross, avg
    - vw_whatsapp_facts: delivered, read, error, total
    """
    with engine.begin() as conn:
        # Payments facts
        conn.execute(text(
            """
            CREATE VIEW IF NOT EXISTS vw_payments_facts AS
            SELECT
              COUNT(*) AS payments_count,
              COALESCE(SUM(amount_cents), 0) AS payments_gross_amount_cents,
              COALESCE(AVG(amount_cents), 0.0) AS payments_avg_amount_cents
            FROM payments;
            """
        ))
        # WhatsApp facts
        conn.execute(text(
            """
            CREATE VIEW IF NOT EXISTS vw_whatsapp_facts AS
            SELECT
              (SELECT COUNT(*) FROM whatsapp_status_events WHERE status='delivered') AS delivered,
              (SELECT COUNT(*) FROM whatsapp_status_events WHERE status='read') AS read,
              (SELECT COUNT(*) FROM whatsapp_status_events WHERE status='error') AS error,
              (SELECT COUNT(*) FROM whatsapp_status_events) AS total
            ;
            """
        ))