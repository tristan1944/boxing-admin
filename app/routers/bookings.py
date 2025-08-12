from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import Booking, Event, Member, Group, MemberVisit
from ..schemas import BookingCreate, BookingAction, BookingOut, BookingsListResponse


router = APIRouter(prefix="/api", tags=["bookings"], dependencies=[Depends(require_token)])


def _event_requires_approval(db: Session, event: Event, member: Member) -> bool:
    if event.requires_approval:
        return True
    if event.group_id:
        group = db.get(Group, event.group_id)
        if group and group.requires_approval:
            return True
    # if any of member's groups require approval
    for g in member.groups:
        if g.requires_approval:
            return True
    return False


@router.post("/bookings.create", response_model=BookingOut)
def bookings_create(payload: BookingCreate, db: Session = Depends(get_db)):
    event: Optional[Event] = db.get(Event, payload.event_id)
    member: Optional[Member] = db.get(Member, payload.member_id)
    if not event or not member:
        raise HTTPException(status_code=400, detail="Invalid event_id or member_id")

    # Capacity check for approved bookings only
    if event.capacity is not None and event.capacity >= 0:
        approved_count = db.execute(
            select(func.count()).select_from(Booking).where(
                and_(Booking.event_id == event.id, Booking.status == "approved")
            )
        ).scalar_one()
        if approved_count >= event.capacity:
            raise HTTPException(status_code=400, detail="Event at capacity")

    status_value = "pending" if _event_requires_approval(db, event, member) else "approved"

    booking = Booking(
        id=str(uuid.uuid4()),
        event_id=event.id,
        member_id=member.id,
        status=status_value,
    )
    db.add(booking)

    if status_value == "approved":
        member.attendance_count = (member.attendance_count or 0) + 1
        db.add(member)
        # record visit
        db.add(MemberVisit(member_id=member.id, event_id=event.id, source="booking_approve"))

    db.commit()
    db.refresh(booking)
    return booking


@router.post("/bookings.approve", response_model=BookingOut)
def bookings_approve(payload: BookingAction, db: Session = Depends(get_db)):
    booking: Optional[Booking] = db.get(Booking, payload.id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status == "approved":
        return booking

    event = db.get(Event, booking.event_id)
    if event and event.capacity is not None and event.capacity >= 0:
        approved_count = db.execute(
            select(func.count()).select_from(Booking).where(
                and_(Booking.event_id == event.id, Booking.status == "approved")
            )
        ).scalar_one()
        if approved_count >= event.capacity:
            raise HTTPException(status_code=400, detail="Event at capacity")

    booking.status = "approved"
    booking.approved_by = payload.approved_by

    member = db.get(Member, booking.member_id)
    if member:
        member.attendance_count = (member.attendance_count or 0) + 1
        db.add(member)
        # record visit
        db.add(MemberVisit(member_id=member.id, event_id=event.id if event else None, source="booking_approve"))

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/bookings.cancel", response_model=BookingOut)
def bookings_cancel(payload: BookingAction, db: Session = Depends(get_db)):
    booking: Optional[Booking] = db.get(Booking, payload.id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "cancelled"
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/bookings.list", response_model=BookingsListResponse)
def bookings_list(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    event_id: Optional[str] = None,
    member_id: Optional[str] = None,
    status: Optional[str] = None,
):
    stmt = select(Booking)
    if event_id:
        stmt = stmt.where(Booking.event_id == event_id)
    if member_id:
        stmt = stmt.where(Booking.member_id == member_id)
    if status:
        stmt = stmt.where(Booking.status == status)

    total = db.execute(stmt.order_by(Booking.created_at.desc())).scalars().all()
    items = total[(page - 1) * page_size : page * page_size]
    return {"items": items, "total": len(total)}


