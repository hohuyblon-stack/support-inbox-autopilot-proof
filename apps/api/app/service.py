from dataclasses import dataclass
from time import perf_counter
from typing import Any

from readiness import evaluate_ticket, record_human_review

from .providers import collect_context, provider_output_for


@dataclass(frozen=True)
class TicketSnapshot:
    external_id: str
    intent: str
    message: str
    order_id: str | None
    tracking_status: str | None
    approved_source_ids: tuple[str, ...]
    policy_conflict: bool
    provider_mode: str


def snapshot_ticket(ticket: Any) -> TicketSnapshot:
    """Copy scalar inputs so provider waits never retain an ORM session object."""

    return TicketSnapshot(
        external_id=ticket.external_id,
        intent=ticket.intent,
        message=ticket.message,
        order_id=ticket.order_id,
        tracking_status=ticket.tracking_status,
        approved_source_ids=tuple(ticket.approved_source_ids),
        policy_conflict=ticket.policy_conflict,
        provider_mode=ticket.provider_mode,
    )


class StaticProvider:
    def __init__(self, output: dict[str, Any]):
        self.output = output

    def generate(self, ticket: dict[str, Any]) -> dict[str, Any]:
        return self.output


class TimeoutProvider:
    def generate(self, ticket: dict[str, Any]) -> dict[str, Any]:
        raise TimeoutError("safe timeout category")


def engine_ticket(ticket: Any) -> dict[str, Any]:
    return {
        "ticket_id": ticket.external_id,
        "intent": ticket.intent,
        "message": ticket.message,
        "context": {
            "order_id": ticket.order_id,
            "tracking_status": ticket.tracking_status,
            "approved_source_ids": list(ticket.approved_source_ids),
            "policy_conflict": ticket.policy_conflict,
        },
    }


async def evaluate_with_context(
    ticket: Any,
    provider: Any,
    *,
    timeout_seconds: float = 0.25,
) -> tuple[dict[str, Any], float]:
    started = perf_counter()
    try:
        context_items = await collect_context(
            provider,
            order_id=ticket.order_id,
            tracking_status=ticket.tracking_status,
            approved_source_ids=ticket.approved_source_ids,
            mode=ticket.provider_mode,
            timeout_seconds=timeout_seconds,
        )
        output = provider_output_for(context_items, mode=ticket.provider_mode)
    except Exception:
        # Adapter exceptions can include request data or credentials. Collapse
        # every ordinary provider failure to the same safe public category;
        # cancellation still propagates because CancelledError is a BaseException.
        decision = evaluate_ticket(engine_ticket(ticket), TimeoutProvider())
    else:
        # Keep deterministic policy-engine defects visible to tests and error
        # monitoring instead of misclassifying them as provider failures.
        decision = evaluate_ticket(engine_ticket(ticket), StaticProvider(output))
    elapsed_ms = (perf_counter() - started) * 1000
    return decision, round(elapsed_ms, 3)


def reviewed_decision(evaluation: Any, status: str, note: str) -> dict[str, Any]:
    return record_human_review(
        {
            "route": evaluation.route,
            "automatic_send_allowed": evaluation.automatic_send_allowed,
            "human_review_status": evaluation.human_review_status,
            "external_action_state": evaluation.external_action_state,
        },
        status,
        note,
    )
