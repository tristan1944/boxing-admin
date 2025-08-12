from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import Member, Group
from ..schemas import MemberCreate, MemberUpdate, MembersListResponse, MemberOut
from ..utils import compute_demographic_segment


router = APIRouter(prefix="/api", tags=["members"], dependencies=[Depends(require_token)])


@router.post("/members.create", response_model=MemberOut)
def members_create(payload: MemberCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    member_id = str(uuid.uuid4())
    demographic = compute_demographic_segment(payload.dob, payload.gender)
    member = Member(
        id=member_id,
        full_name=payload.full_name,
        gender=payload.gender,
        dob=payload.dob,
        phone=payload.phone,
        email=payload.email,
        emergency_contact=payload.emergency_contact,
        membership_type=payload.membership_type,
        join_date=payload.join_date,
        preferred_classes=payload.preferred_classes,
        notes=payload.notes,
        demographic_segment=demographic,
        status=payload.status or "active",
        source=payload.source,
        facebook_campaign_id=payload.facebook_campaign_id,
        referral_note=payload.referral_note,
    )
    if payload.group_ids:
        groups = db.execute(select(Group).where(Group.id.in_(payload.group_ids))).scalars().all()
        member.groups = groups
    db.add(member)
    db.commit()
    db.refresh(member)

    # embed asynchronously
    from ..embedding_tasks import upsert_entity_embedding
    background_tasks.add_task(upsert_entity_embedding, "member", member.id)
    return _member_out(member)


@router.post("/members.update", response_model=MemberOut)
def members_update(payload: MemberUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    member: Optional[Member] = db.get(Member, payload.id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    for field in [
        "full_name",
        "gender",
        "dob",
        "phone",
        "email",
        "emergency_contact",
        "membership_type",
        "notes",
        "preferred_classes",
        "status",
        "source",
        "facebook_campaign_id",
        "referral_note",
    ]:
        value = getattr(payload, field)
        if value is not None:
            setattr(member, field, value)

    # recompute demographic if dob or gender changed
    member.demographic_segment = compute_demographic_segment(member.dob, member.gender)

    if payload.group_ids is not None:
        groups = db.execute(select(Group).where(Group.id.in_(payload.group_ids))).scalars().all()
        member.groups = groups

    db.add(member)
    db.commit()
    db.refresh(member)

    from ..embedding_tasks import upsert_entity_embedding
    background_tasks.add_task(upsert_entity_embedding, "member", member.id)
    return _member_out(member)


@router.get("/members.list", response_model=MembersListResponse)
def members_list(
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    status: Optional[str] = None,
    source: Optional[str] = None,
    group_id: Optional[str] = None,
):
    stmt = select(Member)
    if status:
        stmt = stmt.where(Member.status == status)
    if source:
        stmt = stmt.where(Member.source == source)
    if group_id:
        stmt = stmt.join(Member.groups).where(Group.id == group_id)

    total = db.execute(stmt).scalars().unique().all()
    items = total[(page - 1) * page_size : page * page_size]
    return {
        "items": [_member_out(m) for m in items],
        "total": len(total),
    }


def _member_out(m: Member) -> MemberOut:
    return MemberOut(
        id=m.id,
        full_name=m.full_name,
        gender=m.gender,
        dob=m.dob,
        phone=m.phone,
        email=m.email,
        emergency_contact=m.emergency_contact,
        membership_type=m.membership_type,
        join_date=m.join_date,
        last_active=m.last_active,
        attendance_count=m.attendance_count,
        preferred_classes=m.preferred_classes,
        demographic_segment=m.demographic_segment,
        status=m.status,
        source=m.source,
        facebook_campaign_id=m.facebook_campaign_id,
        referral_note=m.referral_note,
        group_ids=[g.id for g in m.groups] if m.groups else [],
    )


