from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import Group
from ..schemas import GroupCreate, GroupUpdate, GroupsListResponse, GroupOut


router = APIRouter(prefix="/api", tags=["groups"], dependencies=[Depends(require_token)])


@router.post("/groups.create", response_model=GroupOut)
def groups_create(payload: GroupCreate, db: Session = Depends(get_db)):
    if db.get(Group, payload.id):
        raise HTTPException(status_code=400, detail="Group id already exists")
    g = Group(id=payload.id, name=payload.name, requires_approval=payload.requires_approval)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@router.post("/groups.update", response_model=GroupOut)
def groups_update(payload: GroupUpdate, db: Session = Depends(get_db)):
    g = db.get(Group, payload.id)
    if not g:
        raise HTTPException(status_code=404, detail="Not found")
    if payload.name is not None:
        g.name = payload.name
    if payload.requires_approval is not None:
        g.requires_approval = payload.requires_approval
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@router.get("/groups.list", response_model=GroupsListResponse)
def groups_list(db: Session = Depends(get_db), page: int = Query(default=1, ge=1), page_size: int = Query(default=100, ge=1, le=500)):
    rows = db.execute(select(Group)).scalars().all()
    items = rows[(page - 1) * page_size : page * page_size]
    return {"items": items, "total": len(rows)}


