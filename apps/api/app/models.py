from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'evaluated')",
            name="ck_tickets_status",
        ),
        Index("ix_tickets_status_created_at_id", "status", "created_at", "id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    external_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    intent: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    order_id: Mapped[Optional[str]] = mapped_column(String(120))
    tracking_status: Mapped[Optional[str]] = mapped_column(String(80))
    approved_source_ids: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    policy_conflict: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    provider_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="success")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    evaluations: Mapped[List["Evaluation"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
    )


class Evaluation(Base):
    __tablename__ = "evaluations"
    __table_args__ = (
        CheckConstraint(
            "route IN ('draft', 'action', 'escalate')",
            name="ck_evaluations_route",
        ),
        CheckConstraint(
            "human_review_status IN ('pending', 'approved', 'rejected')",
            name="ck_evaluations_review_status",
        ),
        CheckConstraint(
            "external_action_state IN ('blocked', 'ready_for_authorized_human_send')",
            name="ck_evaluations_external_action_state",
        ),
        CheckConstraint(
            "automatic_send_allowed = false",
            name="ck_evaluations_no_automatic_send",
        ),
        UniqueConstraint("ticket_id", name="uq_evaluations_ticket"),
        Index("ix_evaluations_ticket_created_at", "ticket_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    route: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    draft: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    automatic_send_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    human_review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    human_review_note: Mapped[Optional[str]] = mapped_column(Text)
    external_action_state: Mapped[str] = mapped_column(
        String(50), nullable=False, default="blocked"
    )
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    ticket: Mapped[Ticket] = relationship(back_populates="evaluations")
    citation_rows: Mapped[List["EvaluationCitation"]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="EvaluationCitation.source_id",
    )


class EvaluationCitation(Base):
    __tablename__ = "evaluation_citations"
    __table_args__ = (
        UniqueConstraint("evaluation_id", "source_id", name="uq_evaluation_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    evaluation_id: Mapped[str] = mapped_column(
        ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)

    evaluation: Mapped[Evaluation] = relationship(back_populates="citation_rows")
