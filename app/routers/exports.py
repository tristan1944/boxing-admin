from __future__ import annotations

import csv
import io
from typing import Iterable, Optional, List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import Member, Event, Booking


router = APIRouter(prefix="/api", tags=["exports"], dependencies=[Depends(require_token)])


def _stream_csv(rows: Iterable[dict], filename: str, header_fields: Optional[List[str]] = None) -> StreamingResponse:
    buffer = io.StringIO()
    writer: Optional[csv.DictWriter] = None
    row_iter = iter(rows)
    first_row = next(row_iter, None)
    # Determine fieldnames
    if header_fields is not None:
        fieldnames = header_fields
    elif first_row is not None:
        fieldnames = list(first_row.keys())
    else:
        fieldnames = []
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    if first_row is not None:
        writer.writerow(first_row)
    for row in row_iter:
        writer.writerow(row)
    buffer.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/export.members.csv")
def export_members(db: Session = Depends(get_db)):
    items = db.execute(select(Member)).scalars().all()
    rows = (
        {
            "id": m.id,
            "full_name": m.full_name,
            "gender": m.gender or "",
            "dob": m.dob.isoformat() if m.dob else "",
            "phone": m.phone or "",
            "email": m.email or "",
            "membership_type": m.membership_type or "",
            "join_date": m.join_date.isoformat() if m.join_date else "",
            "last_active": m.last_active.isoformat() if m.last_active else "",
            "attendance_count": m.attendance_count,
            "status": m.status,
            "source": m.source or "",
        }
        for m in items
    )
    return _stream_csv(
        rows,
        "members.csv",
        header_fields=[
            "id",
            "full_name",
            "gender",
            "dob",
            "phone",
            "email",
            "membership_type",
            "join_date",
            "last_active",
            "attendance_count",
            "status",
            "source",
        ],
    )


@router.get("/export.events.csv")
def export_events(db: Session = Depends(get_db)):
    items = db.execute(select(Event)).scalars().all()
    rows = (
        {
            "id": e.id,
            "name": e.name,
            "class_type_id": e.class_type_id,
            "group_id": e.group_id or "",
            "start": e.start.isoformat(),
            "end": e.end.isoformat(),
            "recurrence": e.recurrence,
            "capacity": e.capacity if e.capacity is not None else "",
            "is_special": str(e.is_special),
            "requires_approval": str(e.requires_approval),
            "created_by": e.created_by or "",
        }
        for e in items
    )
    return _stream_csv(
        rows,
        "events.csv",
        header_fields=[
            "id",
            "name",
            "class_type_id",
            "group_id",
            "start",
            "end",
            "recurrence",
            "capacity",
            "is_special",
            "requires_approval",
            "created_by",
        ],
    )


@router.get("/export.bookings.csv")
def export_bookings(db: Session = Depends(get_db)):
    items = db.execute(select(Booking)).scalars().all()
    rows = (
        {
            "id": b.id,
            "event_id": b.event_id,
            "member_id": b.member_id,
            "status": b.status,
            "created_at": b.created_at.isoformat(),
            "approved_by": b.approved_by or "",
        }
        for b in items
    )
    return _stream_csv(
        rows,
        "bookings.csv",
        header_fields=[
            "id",
            "event_id",
            "member_id",
            "status",
            "created_at",
            "approved_by",
        ],
    )


