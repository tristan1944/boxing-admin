from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import Booking, Event, Member, Payment, Refund, WhatsAppStatusEvent, MemberVisit
from ..schemas import AnalyticsSummary
from ..utils import compute_age, age_band
from ..analytics_math import compute_revenue_cents, compute_refund_rate, compute_whatsapp_delivery_rate
from ..analytics_facts import compute_facts
from ..analytics_kpis import compute_kpis


router = APIRouter(prefix="/api", tags=["analytics"], dependencies=[Depends(require_token)])


@router.get("/analytics.summary", response_model=AnalyticsSummary)
def analytics_summary(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    d30 = now - timedelta(days=30)
    d90 = now - timedelta(days=90)

    # Attendance per class type over 30/90 days (approved bookings only)
    q = (
        select(Event.class_type_id, func.count())
        .join(Booking, Booking.event_id == Event.id)
        .where(and_(Booking.status == "approved", Booking.created_at >= d30))
        .group_by(Event.class_type_id)
    )
    rows30 = db.execute(q).all()
    attendance_30 = {cls: int(cnt) for cls, cnt in rows30}

    q90 = (
        select(Event.class_type_id, func.count())
        .join(Booking, Booking.event_id == Event.id)
        .where(and_(Booking.status == "approved", Booking.created_at >= d90))
        .group_by(Event.class_type_id)
    )
    rows90 = db.execute(q90).all()
    attendance_90 = {cls: int(cnt) for cls, cnt in rows90}

    # Utilization rate: approved_bookings / capacity, averaged across events with capacity
    events_with_capacity = db.execute(
        select(Event.id, Event.capacity).where(Event.capacity.is_not(None))
    ).all()
    utilization_values: list[float] = []
    for event_id, capacity in events_with_capacity:
        if not capacity or capacity <= 0:
            continue
        approved_count = db.execute(
            select(func.count()).select_from(Booking).where(
                and_(Booking.event_id == event_id, Booking.status == "approved")
            )
        ).scalar_one()
        utilization_values.append(min(1.0, float(approved_count) / float(capacity)))
    avg_util = round(sum(utilization_values) / len(utilization_values), 4) if utilization_values else None

    # Active members
    active_members = db.execute(select(func.count()).select_from(Member).where(Member.status == "active")).scalar_one()

    # Demographics
    members = db.execute(select(Member.dob, Member.gender)).all()
    bands: dict[str, int] = defaultdict(int)
    genders: dict[str, int] = defaultdict(int)
    for dob, gender in members:
        a = compute_age(dob)
        b = age_band(a) or "unknown"
        bands[b] += 1
        g = (gender or "other").strip().lower()
        genders[g] += 1

    # Extended KPIs
    revenue_30d = compute_revenue_cents(db, d30, now)
    refund_rate_30d = compute_refund_rate(db, d30, now)
    whatsapp_delivery_30d = compute_whatsapp_delivery_rate(db, d30, now)

    result = AnalyticsSummary(
        attendance_by_class_type_30d=attendance_30,
        attendance_by_class_type_90d=attendance_90,
        average_utilization_rate=avg_util,
        active_members=int(active_members),
        demographic_age_bands=dict(bands),
        gender_breakdown=dict(genders),
    )

    # Attach extended metrics as optional fields in response (non-breaking: extra keys allowed)
    return {
        **result.model_dump(),
        "revenue_cents_30d": revenue_30d,
        "refund_rate_30d": refund_rate_30d,
        "whatsapp_delivery_rate_30d": whatsapp_delivery_30d,
        # simple totals (no time buckets) for initial analytics
        "totals": {
            "payments": int(db.execute(select(func.count()).select_from(Payment)).scalar_one()),
            "refunds": int(db.execute(select(func.count()).select_from(Refund)).scalar_one()),
            "whatsapp_delivered_or_read": int(
                db.execute(
                    select(func.count()).select_from(WhatsAppStatusEvent).where(
                        WhatsAppStatusEvent.status.in_(["delivered", "read"])  # type: ignore[arg-type]
                    )
                ).scalar_one()
            ),
        },
        "facts": compute_facts(db),
        "kpis": compute_kpis(db),
    }


@router.get("/analytics.totals")
def analytics_totals(db: Session = Depends(get_db)) -> dict:
    """
    EMBED_SUMMARY: Returns overall totals for key entities without time bucketing for fast, stable analytics.
    EMBED_TAGS: analytics, totals, payments, refunds, whatsapp, visits

    SQL sketch:
    SELECT COUNT(*) FROM payments; -- payments
    SELECT COUNT(*) FROM refunds; -- refunds
    SELECT COUNT(*) FROM whatsapp_status_events WHERE status IN ('delivered','read'); -- delivered/read
    SELECT COUNT(*) FROM member_visits; -- attendance atomics
    """
    delivered = db.execute(
        select(func.count()).select_from(WhatsAppStatusEvent).where(WhatsAppStatusEvent.status == "delivered")
    ).scalar_one()
    read = db.execute(
        select(func.count()).select_from(WhatsAppStatusEvent).where(WhatsAppStatusEvent.status == "read")
    ).scalar_one()
    delivered_or_read = db.execute(
        select(func.count()).select_from(WhatsAppStatusEvent).where(WhatsAppStatusEvent.status.in_(["delivered", "read"]))  # type: ignore[arg-type]
    ).scalar_one()
    payments_total = db.execute(select(func.count()).select_from(Payment)).scalar_one()
    refunds_total = db.execute(select(func.count()).select_from(Refund)).scalar_one()
    visits_total = db.execute(select(func.count()).select_from(MemberVisit)).scalar_one()
    return {
        "payments": int(payments_total),
        "refunds": int(refunds_total),
        "whatsapp_delivered": int(delivered),
        "whatsapp_read": int(read),
        "whatsapp_delivered_or_read": int(delivered_or_read),
        "member_visits": int(visits_total),
    }


