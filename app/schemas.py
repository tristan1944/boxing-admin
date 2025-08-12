from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None


# Members
class MemberBase(BaseModel):
    full_name: str
    gender: Optional[str] = None
    dob: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact: Optional[str] = None
    membership_type: Optional[str] = None
    join_date: Optional[date] = None
    preferred_classes: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(default="active")
    source: Optional[str] = None
    facebook_campaign_id: Optional[str] = None
    referral_note: Optional[str] = None
    group_ids: Optional[List[str]] = None


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    id: str
    full_name: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact: Optional[str] = None
    membership_type: Optional[str] = None
    preferred_classes: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    facebook_campaign_id: Optional[str] = None
    referral_note: Optional[str] = None
    group_ids: Optional[List[str]] = None


class MemberOut(BaseModel):
    id: str
    full_name: str
    gender: Optional[str] = None
    dob: Optional[date] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_contact: Optional[str] = None
    membership_type: Optional[str] = None
    join_date: Optional[date] = None
    last_active: Optional[datetime] = None
    attendance_count: int
    preferred_classes: Optional[str] = None
    notes: Optional[str] = None
    demographic_segment: Optional[str] = None
    status: str
    source: Optional[str] = None
    facebook_campaign_id: Optional[str] = None
    referral_note: Optional[str] = None
    group_ids: List[str] = []

    model_config = dict(from_attributes=True)


class MembersListResponse(BaseModel):
    items: List[MemberOut]
    total: int


# Events
class EventBase(BaseModel):
    name: str
    class_type_id: str
    group_id: Optional[str] = None
    start: datetime
    end: datetime
    recurrence: str = Field(default="none")
    capacity: Optional[int] = None
    is_special: bool = False
    requires_approval: bool = False
    created_by: Optional[str] = None
    description: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    id: str
    name: Optional[str] = None
    class_type_id: Optional[str] = None
    group_id: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    recurrence: Optional[str] = None
    capacity: Optional[int] = None
    is_special: Optional[bool] = None
    requires_approval: Optional[bool] = None
    created_by: Optional[str] = None


class EventOut(BaseModel):
    id: str
    name: str
    class_type_id: str
    group_id: Optional[str]
    start: datetime
    end: datetime
    recurrence: str
    capacity: Optional[int]
    is_special: bool
    requires_approval: bool
    created_by: Optional[str]
    description: Optional[str]

    model_config = dict(from_attributes=True)


class EventsListResponse(BaseModel):
    items: List[EventOut]
    total: int


# Bookings
class BookingCreate(BaseModel):
    event_id: str
    member_id: str


class BookingAction(BaseModel):
    id: str
    approved_by: Optional[str] = None


class BookingOut(BaseModel):
    id: str
    event_id: str
    member_id: str
    status: str
    created_at: datetime
    approved_by: Optional[str]

    model_config = dict(from_attributes=True)


class BookingsListResponse(BaseModel):
    items: List[BookingOut]
    total: int


# Analytics
class AnalyticsSummary(BaseModel):
    attendance_by_class_type_30d: dict[str, int]
    attendance_by_class_type_90d: dict[str, int]
    average_utilization_rate: Optional[float]
    active_members: int
    demographic_age_bands: dict[str, int]
    gender_breakdown: dict[str, int]



# ClassTypes
class ClassTypeCreate(BaseModel):
    id: str
    name: str
    level: Optional[str] = None
    description: Optional[str] = None


class ClassTypeUpdate(BaseModel):
    id: str
    name: Optional[str] = None
    level: Optional[str] = None
    description: Optional[str] = None


class ClassTypeOut(BaseModel):
    id: str
    name: str
    level: Optional[str]
    description: Optional[str]

    model_config = dict(from_attributes=True)


class ClassTypesListResponse(BaseModel):
    items: List[ClassTypeOut]
    total: int


# Groups
class GroupCreate(BaseModel):
    id: str
    name: str
    requires_approval: bool = False


class GroupUpdate(BaseModel):
    id: str
    name: Optional[str] = None
    requires_approval: Optional[bool] = None


class GroupOut(BaseModel):
    id: str
    name: str
    requires_approval: bool

    model_config = dict(from_attributes=True)


class GroupsListResponse(BaseModel):
    items: List[GroupOut]
    total: int


# Payments & Refunds
class PaymentCreate(BaseModel):
    member_id: Optional[str] = None
    amount_cents: int
    currency: str = "usd"
    description: Optional[str] = None


class PaymentOut(BaseModel):
    id: str
    created_at: datetime
    member_id: Optional[str]
    amount_cents: int
    currency: str
    status: str
    provider: str
    provider_payment_intent_id: Optional[str]
    provider_charge_id: Optional[str]
    description: Optional[str]
    refunded_amount_cents: int

    model_config = dict(from_attributes=True)


class PaymentsListResponse(BaseModel):
    items: List[PaymentOut]
    total: int


class RefundCreate(BaseModel):
    payment_id: str
    amount_cents: int
    reason: Optional[str] = None


class RefundOut(BaseModel):
    id: str
    created_at: datetime
    payment_id: str
    amount_cents: int
    reason: Optional[str]
    status: str
    provider_refund_id: Optional[str]

    model_config = dict(from_attributes=True)


class RefundsListResponse(BaseModel):
    items: List[RefundOut]
    total: int

