from __future__ import annotations

import hashlib
from typing import Optional

from sqlalchemy import select

from .database import SessionLocal
from .embeddings import get_embedding_provider
from .models import Embedding, Member, Event, ClassType


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
    raise ValueError(f"Unsupported entity_type: {entity_type}")


def _load_entity(db, entity_type: str, entity_id: str):
    if entity_type == "member":
        return db.get(Member, entity_id)
    if entity_type == "event":
        return db.get(Event, entity_id)
    if entity_type == "class_type":
        return db.get(ClassType, entity_id)
    raise ValueError(f"Unsupported entity_type: {entity_type}")


def upsert_entity_embedding(entity_type: str, entity_id: str) -> None:
    db = SessionLocal()
    try:
        obj = _load_entity(db, entity_type, entity_id)
        if not obj:
            return
        text = _text_for_entity(entity_type, obj)
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        provider = get_embedding_provider()
        vector = provider.embed_texts([text])[0]

        existing: Optional[Embedding] = db.execute(
            select(Embedding).where(Embedding.entity_type == entity_type, Embedding.entity_id == entity_id)
        ).scalar_one_or_none()
        if existing:
            if existing.text_hash == text_hash:
                return
            existing.text_hash = text_hash
            existing.vector = vector
            existing.text = text
            db.add(existing)
        else:
            db.add(
                Embedding(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    text_hash=text_hash,
                    vector=vector,
                    text=text,
                )
            )
        db.commit()
    finally:
        db.close()


