from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import SystemLog, StripeWebhook, Payment, Refund
import uuid


router = APIRouter(prefix="/api", tags=["stripe"], dependencies=[Depends(require_token)])
"""
EMBED_SUMMARY: Stripe webhook stub storing raw payloads and extracted event types for analytics.
EMBED_TAGS: stripe, webhooks, payments, analytics
"""


def _upsert_payment_from_intent(db: Session, obj: dict, status: str) -> None:
    intent_id = obj.get("id")
    amount = obj.get("amount_received") or obj.get("amount") or 0
    currency = obj.get("currency") or "usd"
    # find by provider_payment_intent_id
    p = db.execute(
        db.query(Payment).where(Payment.provider_payment_intent_id == intent_id).statement
    ).scalars().first()
    if not p:
        p = Payment(
            id=str(uuid.uuid4()),
            amount_cents=int(amount or 0),
            currency=currency,
            status=status,
            provider="stripe",
            provider_payment_intent_id=intent_id,
        )
    else:
        p.status = status
        if amount:
            p.amount_cents = int(amount)
        p.currency = currency or p.currency
    db.add(p)


def _upsert_payment_from_charge(db: Session, obj: dict, status: str) -> Payment:
    charge_id = obj.get("id")
    amount = obj.get("amount") or 0
    currency = obj.get("currency") or "usd"
    # find by provider_charge_id
    p = db.execute(db.query(Payment).where(Payment.provider_charge_id == charge_id).statement).scalars().first()
    if not p:
        p = Payment(
            id=str(uuid.uuid4()),
            amount_cents=int(amount or 0),
            currency=currency,
            status=status,
            provider="stripe",
            provider_charge_id=charge_id,
        )
    else:
        p.status = status
        if amount:
            p.amount_cents = int(amount)
        p.currency = currency or p.currency
    db.add(p)
    return p


@router.post("/stripe.webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.body()
    text = payload.decode("utf-8", errors="ignore")
    event_type = None
    try:
        import json as _json

        j = _json.loads(text or "{}")
        event_type = (j.get("type") or "").strip()
        obj = (j.get("data") or {}).get("object") or {}
        if event_type.startswith("payment_intent."):
            status = "succeeded" if event_type.endswith("succeeded") else (
                "failed" if event_type.endswith("payment_failed") else "created"
            )
            _upsert_payment_from_intent(db, obj, status)
        elif event_type.startswith("charge."):
            # charge.succeeded, charge.refunded
            status = "succeeded" if event_type.endswith("succeeded") else "updated"
            p = _upsert_payment_from_charge(db, obj, status)
            # handle refund events
            if event_type.endswith("refunded"):
                refunds = (obj.get("refunds") or {}).get("data") or []
                if refunds:
                    r0 = refunds[0]
                    amount_refunded = r0.get("amount") or obj.get("amount_refunded") or 0
                    provider_refund_id = r0.get("id")
                else:
                    amount_refunded = obj.get("amount_refunded") or 0
                    provider_refund_id = None
                if amount_refunded and p:
                    ref = Refund(
                        id=str(uuid.uuid4()),
                        payment_id=p.id,
                        amount_cents=int(amount_refunded),
                        reason="stripe_charge_refund",
                        status="succeeded",
                        provider_refund_id=provider_refund_id,
                    )
                    p.refunded_amount_cents = (p.refunded_amount_cents or 0) + int(amount_refunded)
                    db.add(ref)
                    db.add(p)
    except Exception:
        # ignore parse errors, still log
        pass
    # always persist webhook record and system log
    db.add(StripeWebhook(event_type=event_type, payload=text))
    db.add(SystemLog(actor="stripe", action="webhook", status="received", message=text))
    db.commit()
    return {"ok": True, "event_type": event_type}


