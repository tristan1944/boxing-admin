from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_db
from ..models import Member, SystemLog, MemberVisit


router = APIRouter(tags=["qr"])  # public GET for prototype


@router.get("/checkin")
def qr_checkin(token: str = Query(...), member_id: str = Query(...), db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if token != settings.qr_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.attendance_count = (member.attendance_count or 0) + 1
    member.last_active = datetime.utcnow()
    db.add(member)
    db.add(SystemLog(actor="qr", action="checkin", entity="member", entity_id=member_id, status="ok"))
    db.add(MemberVisit(member_id=member_id, event_id=None, source="qr_checkin"))
    db.commit()
    return {"ok": True, "member_id": member_id}


