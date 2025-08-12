from __future__ import annotations

"""
EMBED_SUMMARY: Derived analytics KPIs with no time bucketing, computed in isolation from facts per domain.
EMBED_TAGS: analytics, kpis, payments, refunds, bookings, whatsapp, visits, utilization

KPIs:
- payments_success_rate = count(Payment.status='succeeded') / max(1, count(Payment))
- refunds_per_payment_rate = count(Refund) / max(1, count(Payment))
- whatsapp_error_rate = count(WhatsAppStatusEvent.status='error') / max(1, count(WhatsAppStatusEvent))
- booking_approval_rate = count(Booking.status='approved') / max(1, count(Booking))
- visits_avg_per_member = count(MemberVisit) / max(1, count(DISTINCT member_id))
- event_capacity_utilization_avg = average(min(1.0, approved_bookings / capacity)) for events with capacity

SQL sketches:
- Success rate: SELECT CAST(SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) AS FLOAT) / MAX(1, COUNT(*)) FROM payments;
- Error rate: SELECT CAST(SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) AS FLOAT) / MAX(1, COUNT(*)) FROM whatsapp_status_events;
- Approval rate: SELECT CAST(SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS FLOAT) / MAX(1, COUNT(*)) FROM bookings;
- Visits avg: SELECT CAST(COUNT(*) AS FLOAT) / MAX(1, COUNT(DISTINCT member_id)) FROM member_visits;
"""

from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from .models import Payment, Refund, WhatsAppStatusEvent, Booking, MemberVisit, Event


def compute_kpis(db: Session) -> dict:
    payments_total = db.execute(select(func.count()).select_from(Payment)).scalar_one() or 0
    payments_succeeded = db.execute(
        select(func.count()).select_from(Payment).where(Payment.status == "succeeded")
    ).scalar_one() or 0
    refunds_total = db.execute(select(func.count()).select_from(Refund)).scalar_one() or 0

    whats_total = db.execute(select(func.count()).select_from(WhatsAppStatusEvent)).scalar_one() or 0
    whats_error = db.execute(
        select(func.count()).select_from(WhatsAppStatusEvent).where(WhatsAppStatusEvent.status == "error")
    ).scalar_one() or 0

    bookings_total = db.execute(select(func.count()).select_from(Booking)).scalar_one() or 0
    bookings_approved = db.execute(
        select(func.count()).select_from(Booking).where(Booking.status == "approved")
    ).scalar_one() or 0

    visits_total = db.execute(select(func.count()).select_from(MemberVisit)).scalar_one() or 0
    visits_unique_members = db.execute(
        select(func.count(func.distinct(MemberVisit.member_id))).select_from(MemberVisit)
    ).scalar_one() or 0

    # Utilization average across events with capacity
    events_with_capacity = db.execute(
        select(Event.id, Event.capacity).where(Event.capacity.is_not(None))
    ).all()
    util_values = []
    for event_id, capacity in events_with_capacity:
        if not capacity or capacity <= 0:
            continue
        approved_count = db.execute(
            select(func.count()).select_from(Booking).where(and_(Booking.event_id == event_id, Booking.status == "approved"))
        ).scalar_one() or 0
        util_values.append(min(1.0, float(approved_count) / float(capacity)))
    utilization_avg = round(sum(util_values) / len(util_values), 4) if util_values else None

    def safe_rate(n: int, d: int) -> Optional[float]:
        if d <= 0:
            return None
        return float(n) / float(d)

    return {
        "payments_success_rate": safe_rate(int(payments_succeeded), int(payments_total)),
        "refunds_per_payment_rate": safe_rate(int(refunds_total), int(payments_total)),
        "whatsapp_error_rate": safe_rate(int(whats_error), int(whats_total)),
        "booking_approval_rate": safe_rate(int(bookings_approved), int(bookings_total)),
        "visits_avg_per_member": safe_rate(int(visits_total), int(visits_unique_members)),
        "event_capacity_utilization_avg": utilization_avg,
    }


