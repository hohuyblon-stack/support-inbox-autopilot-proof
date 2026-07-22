"""Create support-readiness ticket, evaluation, and citation relations.

Revision ID: 0001_initial
Revises: None
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("intent", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("order_id", sa.String(length=120), nullable=True),
        sa.Column("tracking_status", sa.String(length=80), nullable=True),
        sa.Column("approved_source_ids", sa.JSON(), nullable=False),
        sa.Column("policy_conflict", sa.Boolean(), nullable=False),
        sa.Column("provider_mode", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'evaluated')",
            name="ck_tickets_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(
        "ix_tickets_status_created_at_id",
        "tickets",
        ["status", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("route", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=120), nullable=False),
        sa.Column("draft", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("automatic_send_allowed", sa.Boolean(), nullable=False),
        sa.Column("human_review_status", sa.String(length=20), nullable=False),
        sa.Column("human_review_note", sa.Text(), nullable=True),
        sa.Column("external_action_state", sa.String(length=50), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "automatic_send_allowed = false",
            name="ck_evaluations_no_automatic_send",
        ),
        sa.CheckConstraint(
            "external_action_state IN ('blocked', 'ready_for_authorized_human_send')",
            name="ck_evaluations_external_action_state",
        ),
        sa.CheckConstraint(
            "human_review_status IN ('pending', 'approved', 'rejected')",
            name="ck_evaluations_review_status",
        ),
        sa.CheckConstraint(
            "route IN ('draft', 'action', 'escalate')",
            name="ck_evaluations_route",
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_id", name="uq_evaluations_ticket"),
    )
    op.create_index(
        "ix_evaluations_ticket_created_at",
        "evaluations",
        ["ticket_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "evaluation_citations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("evaluation_id", sa.String(length=36), nullable=False),
        sa.Column("source_id", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"],
            ["evaluations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_id",
            "source_id",
            name="uq_evaluation_source",
        ),
    )


def downgrade() -> None:
    op.drop_table("evaluation_citations")
    op.drop_index("ix_evaluations_ticket_created_at", table_name="evaluations")
    op.drop_table("evaluations")
    op.drop_index("ix_tickets_status_created_at_id", table_name="tickets")
    op.drop_table("tickets")
