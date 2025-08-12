from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Union
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import SystemLog, WhatsAppMessage, WhatsAppStatusEvent
import uuid


class WhatsAppSend(BaseModel):
    group_id: str
    message: str


router = APIRouter(prefix="/api", tags=["whatsapp"], dependencies=[Depends(require_token)])
"""
EMBED_SUMMARY: WhatsApp stub endpoint logging outbound group messages and persisting message records.
EMBED_TAGS: whatsapp, messaging, analytics, stubs
"""


@router.post("/whatsapp.sendGroup")
def whatsapp_send_group(payload: WhatsAppSend, db: Session = Depends(get_db)) -> dict:
    log = SystemLog(actor="whatsapp", action="sendGroup", entity="group", entity_id=payload.group_id, status="queued", message=payload.message)
    db.add(
        WhatsAppMessage(
            id=str(uuid.uuid4()),
            group_id=payload.group_id,
            content=payload.message,
            status="queued",
        )
    )
    db.add(log)
    db.commit()
    return {"ok": True}


class WhatsAppStatusIn(BaseModel):
    message_id: str
    status: str  # delivered|read|error
    error_code: Optional[str] = None


class WhatsAppStatusAlt(BaseModel):
    # Accept alternate provider payload shapes
    messageId: str
    state: str
    errorCode: Optional[str] = None


@router.post("/whatsapp.status")
def whatsapp_status(payload: Union[WhatsAppStatusIn, WhatsAppStatusAlt], db: Session = Depends(get_db)) -> dict:
    # normalize
    if hasattr(payload, "messageId"):
        message_id = getattr(payload, "messageId")
        status = getattr(payload, "state")
        error_code = getattr(payload, "errorCode", None)
    else:
        message_id = payload.message_id  # type: ignore[attr-defined]
        status = payload.status  # type: ignore[attr-defined]
        error_code = getattr(payload, "error_code", None)

    status = (status or "").strip().lower()
    if status not in {"delivered", "read", "error"}:
        # map common aliases
        alias_map = {"sent": "delivered", "seen": "read", "failed": "error"}
        status = alias_map.get(status, status)

    db.add(
        WhatsAppStatusEvent(
            message_id=message_id,
            status=status,
            error_code=error_code,
        )
    )
    # Optionally update message table status (best effort)
    m = db.get(WhatsAppMessage, message_id)
    if m:
        m.status = status
        db.add(m)
    db.commit()
    return {"ok": True}


