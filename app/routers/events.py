from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import Event, ClassType, Group
from ..schemas import EventCreate, EventUpdate, EventOut, EventsListResponse


router = APIRouter(prefix="/api", tags=["events"], dependencies=[Depends(require_token)])


@router.post("/events.create", response_model=EventOut)
def events_create(payload: EventCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Validate FKs
    if not db.get(ClassType, payload.class_type_id):
        raise HTTPException(status_code=400, detail="Invalid class_type_id")
    if payload.group_id and not db.get(Group, payload.group_id):
        raise HTTPException(status_code=400, detail="Invalid group_id")

    event = Event(
        id=str(uuid.uuid4()),
        name=payload.name,
        class_type_id=payload.class_type_id,
        group_id=payload.group_id,
        start=payload.start,
        end=payload.end,
        recurrence=payload.recurrence or "none",
        capacity=payload.capacity,
        is_special=payload.is_special,
        requires_approval=payload.requires_approval,
        created_by=payload.created_by,
        description=payload.description,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    from ..embedding_tasks import upsert_entity_embedding
    background_tasks.add_task(upsert_entity_embedding, "event", event.id)
    return event


@router.post("/events.update", response_model=EventOut)
def events_update(payload: EventUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    event: Optional[Event] = db.get(Event, payload.id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if payload.class_type_id and not db.get(ClassType, payload.class_type_id):
        raise HTTPException(status_code=400, detail="Invalid class_type_id")
    if payload.group_id and not db.get(Group, payload.group_id):
        raise HTTPException(status_code=400, detail="Invalid group_id")

    for field in [
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
        "description",
    ]:
        value = getattr(payload, field)
        if value is not None:
            setattr(event, field, value)

    db.add(event)
    db.commit()
    db.refresh(event)

    from ..embedding_tasks import upsert_entity_embedding
    background_tasks.add_task(upsert_entity_embedding, "event", event.id)
    return event


@router.get("/events.list", response_model=EventsListResponse)
def events_list(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    is_special: Optional[bool] = None,
    q: Optional[str] = None,
    start_from: Optional[str] = None,
    end_to: Optional[str] = None,
):
    stmt = select(Event)
    if is_special is not None:
        stmt = stmt.where(Event.is_special == is_special)
    if q:
        # Simple case-insensitive contains; SQLite only, portable enough for MVP
        stmt = stmt.where(Event.name.ilike(f"%{q}%"))
    if start_from:
        from datetime import datetime as dt
        stmt = stmt.where(Event.start >= dt.fromisoformat(start_from))
    if end_to:
        from datetime import datetime as dt
        stmt = stmt.where(Event.end <= dt.fromisoformat(end_to))

    total = db.execute(stmt.order_by(Event.start.desc())).scalars().all()
    items = total[(page - 1) * page_size : page * page_size]
    return {"items": items, "total": len(total)}


