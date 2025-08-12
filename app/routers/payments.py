from __future__ import annotations

"""
EMBED_SUMMARY: Payments and refunds endpoints (MVP). Create/list payments and refunds; wire to Stripe later.
EMBED_TAGS: payments, refunds, stripe, analytics, api
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_token
from ..models import Payment, Refund
from ..schemas import (
    PaymentCreate,
    PaymentOut,
    PaymentsListResponse,
    RefundCreate,
    RefundOut,
    RefundsListResponse,
)


router = APIRouter(prefix="/api", tags=["payments"], dependencies=[Depends(require_token)])


@router.post("/payments.create", response_model=PaymentOut)
def payments_create(payload: PaymentCreate, db: Session = Depends(get_db)) -> PaymentOut:
    p = Payment(
        id=str(uuid.uuid4()),
        member_id=payload.member_id,
        amount_cents=payload.amount_cents,
        currency=payload.currency or "usd",
        description=payload.description,
        status="created",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/payments.list", response_model=PaymentsListResponse)
def payments_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    member_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    stmt = select(Payment)
    if member_id:
        stmt = stmt.where(Payment.member_id == member_id)
    if status:
        stmt = stmt.where(Payment.status == status)
    total = db.execute(stmt.order_by(Payment.created_at.desc())).scalars().all()
    items = total[(page - 1) * page_size : page * page_size]
    return {"items": items, "total": len(total)}


@router.post("/refunds.create", response_model=RefundOut)
def refunds_create(payload: RefundCreate, db: Session = Depends(get_db)) -> RefundOut:
    payment = db.get(Payment, payload.payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payload.amount_cents <= 0 or payload.amount_cents > payment.amount_cents - payment.refunded_amount_cents:
        raise HTTPException(status_code=400, detail="Invalid refund amount")
    refund = Refund(
        id=str(uuid.uuid4()),
        payment_id=payment.id,
        amount_cents=payload.amount_cents,
        reason=payload.reason,
        status="requested",
    )
    payment.refunded_amount_cents += payload.amount_cents
    db.add(payment)
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund


@router.get("/refunds.list", response_model=RefundsListResponse)
def refunds_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    payment_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    stmt = select(Refund)
    if payment_id:
        stmt = stmt.where(Refund.payment_id == payment_id)
    total = db.execute(stmt.order_by(Refund.created_at.desc())).scalars().all()
    items = total[(page - 1) * page_size : page * page_size]
    return {"items": items, "total": len(total)}


