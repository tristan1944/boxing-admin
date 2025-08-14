from __future__ import annotations

"""
EMBED_SUMMARY: Core data models for members, classes, events, bookings, and analytics-supporting entities.
EMBED_TAGS: models, payments, refunds, whatsapp, analytics, schema
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base


# Association table for many-to-many between members and groups
member_groups = Table(
    "member_groups",
    Base.metadata,
    Column("member_id", String(36), ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", String(64), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)


class FacebookCampaign(Base):
    __tablename__ = "facebook_campaigns"
    """
    EMBED_SUMMARY: Marketing attribution source for members/bookings; used to segment performance.
    EMBED_TAGS: marketing, facebook, attribution, campaigns
    """

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default="facebook", nullable=False)

    __table_args__ = (
        Index("ix_campaign_active_platform", "platform"),
    )


class ClassType(Base):
    __tablename__ = "class_types"
    """
    EMBED_SUMMARY: Canonical class definitions (e.g., Boxing Basics, Sparring) used by events.
    EMBED_TAGS: classes, catalog, taxonomy
    """

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Group(Base):
    __tablename__ = "groups"
    """
    EMBED_SUMMARY: Logical cohorts (e.g., Youth, Competition Team) affecting approval logic and analytics.
    EMBED_TAGS: groups, cohorts, approvals
    """

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    members: Mapped[list["Member"]] = relationship(
        "Member", secondary=member_groups, back_populates="groups", lazy="selectin"
    )


class Member(Base):
    __tablename__ = "members"
    """
    EMBED_SUMMARY: Gym member profile with demographics and engagement signals for analytics.
    EMBED_TAGS: members, demographics, engagement
    """

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    dob: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    membership_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    join_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    attendance_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    preferred_classes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    demographic_segment: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    facebook_campaign_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("facebook_campaigns.id"), nullable=True
    )
    referral_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    groups: Mapped[list[Group]] = relationship(
        Group, secondary=member_groups, back_populates="members", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_members_status", "status"),
        Index("ix_members_source", "source"),
    )


class Event(Base):
    __tablename__ = "events"
    """
    EMBED_SUMMARY: Scheduled classes/sessions with capacity and approval settings.
    EMBED_TAGS: events, scheduling, capacity
    """

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_type_id: Mapped[str] = mapped_column(String(64), ForeignKey("class_types.id"), nullable=False)
    group_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("groups.id"), nullable=True)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    recurrence: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_special: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    group: Mapped[Optional[Group]] = relationship(Group, lazy="joined")
    class_type: Mapped[ClassType] = relationship(ClassType, lazy="joined")

    __table_args__ = (
        CheckConstraint("end > start", name="ck_event_end_after_start"),
        Index("ix_events_recurrence", "recurrence"),
        Index("ix_events_group_id", "group_id"),
    )


class Booking(Base):
    __tablename__ = "bookings"
    """
    EMBED_SUMMARY: Member registrations for events; enforces capacity and approval rules.
    EMBED_TAGS: bookings, attendance, capacity
    """

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="approved", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    event: Mapped[Event] = relationship(Event, lazy="joined")
    member: Mapped[Member] = relationship(Member, lazy="joined")

    __table_args__ = (
        UniqueConstraint("event_id", "member_id", name="uq_booking_event_member"),
        Index("ix_bookings_status", "status"),
    )


class SystemLog(Base):
    __tablename__ = "system_log"
    """
    EMBED_SUMMARY: Append-only application log for external integrations and actions.
    EMBED_TAGS: logs, audit, integrations
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    actor: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ConfigEntry(Base):
    __tablename__ = "config"
    """
    EMBED_SUMMARY: Simple key/value configuration store.
    EMBED_TAGS: config, settings
    """

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Embedding(Base):
    __tablename__ = "embeddings"
    """
    EMBED_SUMMARY: Persisted vectors for members/events/class types; supports semantic search.
    EMBED_TAGS: embeddings, vectors, search
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vector: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_embedding_entity"),
        Index("ix_embeddings_entity", "entity_type", "entity_id"),
    )



class StripeWebhook(Base):
    __tablename__ = "stripe_webhooks"
    """
    EMBED_SUMMARY: Raw Stripe webhook payloads with extracted event type for analytics and auditing.
    EMBED_TAGS: stripe, webhooks, payments, analytics
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    event_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_stripe_webhook_ts", "ts"),
        Index("ix_stripe_webhook_type", "event_type"),
    )


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"
    """
    EMBED_SUMMARY: Outbound WhatsApp messages; track content, group/member target, and status.
    EMBED_TAGS: whatsapp, messaging, outreach
    """

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    group_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    member_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("members.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="whatsapp", nullable=False)
    provider_ref: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_whatsapp_created_at", "created_at"),
    )


class WhatsAppStatusEvent(Base):
    __tablename__ = "whatsapp_status_events"
    """
    EMBED_SUMMARY: Provider status updates (delivered/read/error) linked to WhatsApp messages.
    EMBED_TAGS: whatsapp, delivery, status, analytics
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("whatsapp_messages.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    provider_ts: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_whatsapp_status_message", "message_id"),
        Index("ix_whatsapp_status_created", "created_at"),
    )


class StripeCustomer(Base):
    __tablename__ = "stripe_customers"
    """
    EMBED_SUMMARY: Mapping from internal member to Stripe customer id.
    EMBED_TAGS: stripe, mapping, customers
    """

    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)


class Payment(Base):
    __tablename__ = "payments"
    """
    EMBED_SUMMARY: Monetary transactions (cents) with provider references; basis for revenue analytics.
    EMBED_TAGS: payments, revenue, stripe, analytics
    """

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    member_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("members.id"), nullable=True, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="usd", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="stripe", nullable=False)
    provider_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    provider_charge_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refunded_amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_payments_created_at", "created_at"),
    )


class Refund(Base):
    __tablename__ = "refunds"
    """
    EMBED_SUMMARY: Refunds linked to payments; used in refund rate and net revenue.
    EMBED_TAGS: refunds, revenue, analytics
    """

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("payments.id", ondelete="CASCADE"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="requested", nullable=False, index=True)
    provider_refund_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_refunds_created_at", "created_at"),
    )


class MemberVisit(Base):
    __tablename__ = "member_visits"
    """
    EMBED_SUMMARY: Atomic attendance records for members, created on booking approval or QR check-in.
    EMBED_TAGS: visits, attendance, analytics
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    member_id: Mapped[str] = mapped_column(String(36), ForeignKey("members.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("events.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_member_visits_ts", "ts"),
    )


class CodeEmbedding(Base):
    __tablename__ = "code_embeddings"
    """
    EMBED_SUMMARY: Persisted code embeddings for building a comprehensive code+math map.
    EMBED_TAGS: code, embeddings, vectors, search, indexing
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(512), index=True)
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    lang: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    chunk_idx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vector: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("path", "chunk_idx", "text_hash", name="uq_code_chunk"),
    )

