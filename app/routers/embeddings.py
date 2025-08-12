from __future__ import annotations

import hashlib
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..embeddings import get_embedding_provider, cosine_similarity
from ..models import Embedding, Member, Event, ClassType


router = APIRouter(prefix="/api", tags=["embeddings"], dependencies=[Depends(require_token)])


def _text_for_entity(entity_type: str, obj) -> str:
    if entity_type == "member":
        return "\n".join(
            [
                obj.full_name or "",
                obj.email or "",
                obj.phone or "",
                obj.membership_type or "",
                obj.notes or "",
                obj.referral_note or "",
            ]
        ).strip()
    if entity_type == "event":
        return "\n".join(
            [
                obj.name or "",
                obj.description or "",
                obj.class_type_id or "",
                obj.group_id or "",
            ]
        ).strip()
    if entity_type == "class_type":
        return "\n".join([obj.name or "", obj.description or "", obj.level or ""]).strip()
    raise HTTPException(status_code=400, detail="Unsupported entity_type")


def _entity_query(db: Session, entity_type: str):
    if entity_type == "member":
        return select(Member)
    if entity_type == "event":
        return select(Event)
    if entity_type == "class_type":
        return select(ClassType)
    raise HTTPException(status_code=400, detail="Unsupported entity_type")


@router.post("/embeddings.backfill")
def embeddings_backfill(db: Session = Depends(get_db), entity_type: Optional[str] = Query(default=None)) -> dict:
    provider = get_embedding_provider()

    entity_types: List[str] = [entity_type] if entity_type else ["member", "event", "class_type"]
    total_updated = 0

    for et in entity_types:
        rows = db.execute(_entity_query(db, et)).scalars().all()
        texts = [_text_for_entity(et, obj) for obj in rows]
        hashes = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts]
        vectors = provider.embed_texts(texts) if rows else []

        for obj, text, text_hash, vector in zip(rows, texts, hashes, vectors):
            # Upsert Embedding record
            existing = db.execute(
                select(Embedding).where(Embedding.entity_type == et, Embedding.entity_id == getattr(obj, "id"))
            ).scalar_one_or_none()
            if existing:
                if existing.text_hash == text_hash:
                    continue
                existing.text_hash = text_hash
                existing.vector = vector
                existing.text = text
                db.add(existing)
            else:
                db.add(
                    Embedding(
                        entity_type=et,
                        entity_id=getattr(obj, "id"),
                        text_hash=text_hash,
                        vector=vector,
                        text=text,
                    )
                )
            total_updated += 1
        db.commit()

    return {"ok": True, "updated": total_updated}


@router.get("/embeddings.search")
def embeddings_search(
    q: str,
    entity_type: str = Query(default="member", pattern="^(member|event|class_type)$"),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    provider = get_embedding_provider()
    query_vec = provider.embed_texts([q])[0]

    records = db.execute(select(Embedding).where(Embedding.entity_type == entity_type)).scalars().all()
    scored = []
    for rec in records:
        if not rec.vector:
            continue
        score = cosine_similarity(query_vec, rec.vector)  # type: ignore[arg-type]
        scored.append((score, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]

    # Resolve entities for return payload
    def resolve(entity_id: str):
        if entity_type == "member":
            return db.get(Member, entity_id)
        if entity_type == "event":
            return db.get(Event, entity_id)
        if entity_type == "class_type":
            return db.get(ClassType, entity_id)
        return None

    items = [
        {
            "score": round(score, 6),
            "entity_type": entity_type,
            "entity_id": rec.entity_id,
            "text": rec.text,
            "item": resolve(rec.entity_id),
        }
        for score, rec in top
    ]
    return {"items": items, "total": len(scored)}


