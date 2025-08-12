from __future__ import annotations

"""
EMBED_SUMMARY: Analytics math helpers for revenue, refund rate, and WhatsApp delivery performance.
EMBED_TAGS: analytics, math, revenue, refunds, refund rate, whatsapp, delivery rate

These helpers compute core KPIs from the relational schema. They should remain deterministic,
well-documented, and easy to test with small fixtures. Formulas:
- revenue_cents = sum(Payment.amount_cents in window) - sum(Refund.amount_cents in window)
- refund_rate = sum(Refund.amount_cents in window) / max(1, sum(Payment.amount_cents in window))
- whatsapp_delivery_rate = delivered_messages / max(1, sent_messages) where delivered_messages are
  distinct message_ids that saw a delivered/read status in the window, and sent_messages are
  WhatsAppMessage rows created in the window.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .models import Payment, Refund, WhatsAppMessage, WhatsAppStatusEvent


def compute_revenue_cents(db: Session, start: datetime, end: datetime) -> int:
    """
    EMBED_SUMMARY: Revenue in cents over a window equals sum(payments.amount_cents) minus sum(refunds.amount_cents).
    EMBED_TAGS: analytics, revenue, payments, refunds, window, sum

    SQL sketch (windowed):
    SELECT
      COALESCE((SELECT SUM(p.amount_cents) FROM payments p WHERE p.created_at BETWEEN :start AND :end), 0)
      -
      COALESCE((SELECT SUM(r.amount_cents) FROM refunds r WHERE r.created_at BETWEEN :start AND :end), 0)
      AS revenue_cents;
    """
    payments_sum = (
        db.execute(
            select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(
                and_(Payment.created_at >= start, Payment.created_at <= end)
            )
        ).scalar_one()
        or 0
    )
    refunds_sum = (
        db.execute(
            select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
                and_(Refund.created_at >= start, Refund.created_at <= end)
            )
        ).scalar_one()
        or 0
    )
    return int(payments_sum) - int(refunds_sum)


def compute_refund_rate(db: Session, start: datetime, end: datetime) -> Optional[float]:
    """
    EMBED_SUMMARY: Refund rate equals sum(refunds.amount_cents) divided by sum(payments.amount_cents) for the window; returns None if no payments.
    EMBED_TAGS: analytics, refund rate, payments, refunds, ratio, window

    SQL sketch (windowed):
    WITH sums AS (
      SELECT
        COALESCE((SELECT SUM(p.amount_cents) FROM payments p WHERE p.created_at BETWEEN :start AND :end), 0) AS pay_sum,
        COALESCE((SELECT SUM(r.amount_cents) FROM refunds r WHERE r.created_at BETWEEN :start AND :end), 0) AS ref_sum
    )
    SELECT CASE WHEN pay_sum <= 0 THEN NULL ELSE CAST(ref_sum AS FLOAT)/CAST(pay_sum AS FLOAT) END AS refund_rate
    FROM sums;
    """
    payments_sum = (
        db.execute(
            select(func.coalesce(func.sum(Payment.amount_cents), 0)).where(
                and_(Payment.created_at >= start, Payment.created_at <= end)
            )
        ).scalar_one()
        or 0
    )
    if payments_sum <= 0:
        return None
    refunds_sum = (
        db.execute(
            select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
                and_(Refund.created_at >= start, Refund.created_at <= end)
            )
        ).scalar_one()
        or 0
    )
    return float(refunds_sum) / float(payments_sum)


def compute_whatsapp_delivery_rate(db: Session, start: datetime, end: datetime) -> Optional[float]:
    """
    EMBED_SUMMARY: WhatsApp delivery rate equals distinct messages with status in (delivered, read) divided by messages sent in window; returns None if none sent.
    EMBED_TAGS: analytics, whatsapp, delivery rate, read, delivered, ratio, window

    SQL sketch (windowed):
    WITH sent AS (
      SELECT COUNT(*) AS cnt FROM whatsapp_messages m
      WHERE m.created_at BETWEEN :start AND :end
    ), delivered AS (
      SELECT COUNT(DISTINCT e.message_id) AS cnt
      FROM whatsapp_status_events e
      WHERE e.status IN ('delivered','read') AND e.created_at BETWEEN :start AND :end
    )
    SELECT CASE WHEN sent.cnt <= 0 THEN NULL ELSE CAST(delivered.cnt AS FLOAT)/CAST(sent.cnt AS FLOAT) END AS delivery_rate
    FROM sent, delivered;
    """
    sent_count = (
        db.execute(
            select(func.count()).select_from(WhatsAppMessage).where(
                and_(WhatsAppMessage.created_at >= start, WhatsAppMessage.created_at <= end)
            )
        ).scalar_one()
        or 0
    )
    if sent_count <= 0:
        return None
    delivered_distinct = (
        db.execute(
            select(func.count(func.distinct(WhatsAppStatusEvent.message_id))).where(
                and_(
                    WhatsAppStatusEvent.status.in_(["delivered", "read"]),
                    WhatsAppStatusEvent.created_at >= start,
                    WhatsAppStatusEvent.created_at <= end,
                )
            )
        ).scalar_one()
        or 0
    )
    return float(delivered_distinct) / float(sent_count)


