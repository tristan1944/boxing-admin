from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import ClassType
from ..schemas import ClassTypeCreate, ClassTypeUpdate, ClassTypesListResponse, ClassTypeOut


router = APIRouter(prefix="/api", tags=["class_types"], dependencies=[Depends(require_token)])


@router.post("/class_types.create", response_model=ClassTypeOut)
def class_types_create(payload: ClassTypeCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if db.get(ClassType, payload.id):
        raise HTTPException(status_code=400, detail="ClassType id already exists")
    ct = ClassType(id=payload.id, name=payload.name, level=payload.level, description=payload.description)
    db.add(ct)
    db.commit()
    db.refresh(ct)
    from ..embedding_tasks import upsert_entity_embedding
    background_tasks.add_task(upsert_entity_embedding, "class_type", ct.id)
    return ct


@router.post("/class_types.update", response_model=ClassTypeOut)
def class_types_update(payload: ClassTypeUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    ct = db.get(ClassType, payload.id)
    if not ct:
        raise HTTPException(status_code=404, detail="Not found")
    for field in ["name", "level", "description"]:
        val = getattr(payload, field)
        if val is not None:
            setattr(ct, field, val)
    db.add(ct)
    db.commit()
    db.refresh(ct)
    from ..embedding_tasks import upsert_entity_embedding
    background_tasks.add_task(upsert_entity_embedding, "class_type", ct.id)
    return ct


@router.get("/class_types.list", response_model=ClassTypesListResponse)
def class_types_list(db: Session = Depends(get_db), page: int = Query(default=1, ge=1), page_size: int = Query(default=100, ge=1, le=500)):
    rows = db.execute(select(ClassType)).scalars().all()
    items = rows[(page - 1) * page_size : page * page_size]
    return {"items": items, "total": len(rows)}


