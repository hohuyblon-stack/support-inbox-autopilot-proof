from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


Intent = Literal[
    "wismo",
    "return_policy",
    "product_question",
    "discount_policy",
    "gift_policy",
    "international_shipping",
    "eligible_return",
    "address_change",
    "cancellation",
    "return_exception",
    "damaged_item",
    "delivered_not_received",
    "chargeback",
    "wholesale",
]
ProviderMode = Literal["success", "timeout", "low_confidence", "bad_citation"]


class TicketCreate(BaseModel):
    external_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    intent: Intent
    message: str = Field(min_length=1, max_length=2000)
    order_id: Optional[str] = Field(default=None, max_length=120)
    tracking_status: Optional[str] = Field(default=None, max_length=80)
    approved_source_ids: list[str] = Field(min_length=1, max_length=10)
    policy_conflict: bool = False
    provider_mode: ProviderMode = "success"

    @field_validator("approved_source_ids")
    @classmethod
    def validate_source_ids(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item or len(item) > 160 for item in normalized):
            raise ValueError("source ids must be non-empty and at most 160 characters")
        if len(set(normalized)) != len(normalized):
            raise ValueError("source ids must be unique")
        return normalized


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    intent: str
    message: str
    status: str
    created_at: datetime


class TicketList(BaseModel):
    items: list[TicketResponse]
    next_cursor: Optional[str]


class EvaluationResponse(BaseModel):
    id: str
    ticket_id: str
    route: str
    reason: str
    draft: Optional[str]
    citations: list[str]
    confidence: Optional[float]
    automatic_send_allowed: bool
    human_review_status: str
    external_action_state: str
    latency_ms: float


class ReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]
    note: str = Field(min_length=1, max_length=500)


class MetricsResponse(BaseModel):
    tickets_total: int
    evaluations_total: int
    routes: dict[str, int]
    automatic_sends: int
