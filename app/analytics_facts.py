from __future__ import annotations

"""
EMBED_SUMMARY: Foundational analytics facts computed directly from SQL without cross-metric math.
EMBED_TAGS: analytics, facts, counts, sums, sql, payments, refunds, bookings, members, events, whatsapp, visits

This module exposes compute_facts(db) returning independent counts/sums:
- Members: total, by_status
- Events: total, with_capacity_count, capacity_sum
- Bookings: total, by_status, unique_members_booked, unique_events_with_bookings
- ClassTypes/Groups/Campaigns: totals
- Payments: count, gross_amount_cents, avg_amount_cents
- Refunds: count, gross_amount_cents
- WhatsApp: messages_total, status_events_total, delivered, read, error, distinct_statused_messages
- MemberVisits: total, unique_members

SQL sketches:
- Members by status: SELECT status, COUNT(*) FROM members GROUP BY status;
- Events capacity sum: SELECT SUM(capacity) FROM events WHERE capacity IS NOT NULL;
- Bookings by status: SELECT status, COUNT(*) FROM bookings GROUP BY status;
- Payments sum: SELECT COALESCE(SUM(amount_cents),0) FROM payments;
- Refunds sum: SELECT COALESCE(SUM(amount_cents),0) FROM refunds;
- WhatsApp delivered/read/error: SELECT COUNT(*) FROM whatsapp_status_events WHERE status='delivered'; ...
- Member visits: SELECT COUNT(*), COUNT(DISTINCT member_id) FROM member_visits;
"""

from typing import Dict
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .models import (
    Member,
    Event,
    Booking,
    ClassType,
    Group,
    FacebookCampaign,
    Payment,
    Refund,
    WhatsAppMessage,
    WhatsAppStatusEvent,
    MemberVisit,
)


def _counts_by_status(db: Session, model, field) -> Dict[str, int]:
    rows = db.execute(select(field, func.count()).select_from(model).group_by(field)).all()
    return {str(status or ""): int(cnt) for status, cnt in rows}


def compute_facts(db: Session) -> dict:
    members_total = db.execute(select(func.count()).select_from(Member)).scalar_one()
    members_by_status = _counts_by_status(db, Member, Member.status)

    events_total = db.execute(select(func.count()).select_from(Event)).scalar_one()
    events_with_capacity = db.execute(
        select(func.count()).select_from(Event).where(Event.capacity.is_not(None))
    ).scalar_one()
    events_capacity_sum = db.execute(
        select(func.coalesce(func.sum(Event.capacity), 0)).where(Event.capacity.is_not(None))
    ).scalar_one()

    bookings_total = db.execute(select(func.count()).select_from(Booking)).scalar_one()
    bookings_by_status = _counts_by_status(db, Booking, Booking.status)
    bookings_unique_members = db.execute(
        select(func.count(func.distinct(Booking.member_id)))
    ).scalar_one()
    bookings_unique_events = db.execute(
        select(func.count(func.distinct(Booking.event_id)))
    ).scalar_one()

    class_types_total = db.execute(select(func.count()).select_from(ClassType)).scalar_one()
    groups_total = db.execute(select(func.count()).select_from(Group)).scalar_one()
    campaigns_total = db.execute(select(func.count()).select_from(FacebookCampaign)).scalar_one()

    payments_count = db.execute(select(func.count()).select_from(Payment)).scalar_one()
    payments_gross = db.execute(
        select(func.coalesce(func.sum(Payment.amount_cents), 0))
    ).scalar_one()
    payments_avg = db.execute(
        select(func.coalesce(func.avg(Payment.amount_cents), 0.0))
    ).scalar_one()

    refunds_count = db.execute(select(func.count()).select_from(Refund)).scalar_one()
    refunds_gross = db.execute(
        select(func.coalesce(func.sum(Refund.amount_cents), 0))
    ).scalar_one()

    whatsapp_messages_total = db.execute(
        select(func.count()).select_from(WhatsAppMessage)
    ).scalar_one()
    whatsapp_events_total = db.execute(
        select(func.count()).select_from(WhatsAppStatusEvent)
    ).scalar_one()
    whatsapp_delivered = db.execute(
        select(func.count()).select_from(WhatsAppStatusEvent).where(WhatsAppStatusEvent.status == "delivered")
    ).scalar_one()
    whatsapp_read = db.execute(
        select(func.count()).select_from(WhatsAppStatusEvent).where(WhatsAppStatusEvent.status == "read")
    ).scalar_one()
    whatsapp_error = db.execute(
        select(func.count()).select_from(WhatsAppStatusEvent).where(WhatsAppStatusEvent.status == "error")
    ).scalar_one()
    whatsapp_distinct_statused_messages = db.execute(
        select(func.count(func.distinct(WhatsAppStatusEvent.message_id)))
    ).scalar_one()

    visits_total = db.execute(select(func.count()).select_from(MemberVisit)).scalar_one()
    visits_unique_members = db.execute(
        select(func.count(func.distinct(MemberVisit.member_id)))
    ).scalar_one()

    return {
        "members": {"total": int(members_total), "by_status": {k: int(v) for k, v in members_by_status.items()}},
        "events": {
            "total": int(events_total),
            "with_capacity_count": int(events_with_capacity),
            "capacity_sum": int(events_capacity_sum or 0),
        },
        "bookings": {
            "total": int(bookings_total),
            "by_status": {k: int(v) for k, v in bookings_by_status.items()},
            "unique_members": int(bookings_unique_members),
            "unique_events": int(bookings_unique_events),
        },
        "class_types": {"total": int(class_types_total)},
        "groups": {"total": int(groups_total)},
        "campaigns": {"total": int(campaigns_total)},
        "payments": {
            "count": int(payments_count),
            "gross_amount_cents": int(payments_gross or 0),
            "avg_amount_cents": float(payments_avg or 0.0),
        },
        "refunds": {"count": int(refunds_count), "gross_amount_cents": int(refunds_gross or 0)},
        "whatsapp": {
            "messages_total": int(whatsapp_messages_total),
            "status_events_total": int(whatsapp_events_total),
            "delivered": int(whatsapp_delivered),
            "read": int(whatsapp_read),
            "error": int(whatsapp_error),
            "distinct_statused_messages": int(whatsapp_distinct_statused_messages),
        },
        "visits": {"total": int(visits_total), "unique_members": int(visits_unique_members)},
    }


