"""Offline control boundary for the synthetic WISMO and returns evaluation.

The module deliberately cannot send messages or mutate an external support
system. It separates deterministic safety routing from an optional draft
provider, validates the provider's structured output, and keeps every result
behind a human-review boundary.
"""

from copy import deepcopy
from typing import Any, Dict, List


DRAFT_INTENTS = {
    "discount_policy",
    "gift_policy",
    "international_shipping",
    "product_question",
    "return_policy",
    "wismo",
}
ADMIN_ACTION_INTENTS = {"address_change", "cancellation", "eligible_return"}
HIGH_RISK_INTENTS = {
    "chargeback",
    "damaged_item",
    "delivered_not_received",
    "return_exception",
    "wholesale",
}
INJECTION_MARKERS = (
    "ignore previous instructions",
    "ignore all instructions",
    "reveal the system prompt",
    "show the system prompt",
)
MINIMUM_DRAFT_CONFIDENCE = 0.8


def _base_result(ticket: Any) -> Dict[str, Any]:
    ticket_id = ticket.get("ticket_id") if isinstance(ticket, dict) else None
    return {
        "ticket_id": ticket_id,
        "route": "escalate",
        "reason": "malformed_input",
        "draft": None,
        "citations": [],
        "confidence": None,
        "automatic_send_allowed": False,
        "human_review_status": "pending",
        "external_action_state": "blocked",
    }


def _validation_issues(ticket: Any) -> List[str]:
    if not isinstance(ticket, dict):
        return ["ticket must be an object"]

    issues = []
    if not isinstance(ticket.get("ticket_id"), str) or not ticket["ticket_id"].strip():
        issues.append("ticket_id is required")
    if not isinstance(ticket.get("intent"), str) or not ticket["intent"].strip():
        issues.append("intent is required")
    if not isinstance(ticket.get("message"), str) or not ticket["message"].strip():
        issues.append("message is required")
    context = ticket.get("context")
    if not isinstance(context, dict):
        issues.append("context must be an object")
        return issues
    approved_sources = context.get("approved_source_ids")
    if (
        not isinstance(approved_sources, list)
        or not approved_sources
        or not all(isinstance(item, str) and item.strip() for item in approved_sources)
    ):
        issues.append("context.approved_source_ids must be a non-empty string list")
    return issues


def _finish(result: Dict[str, Any], route: str, reason: str) -> Dict[str, Any]:
    result["route"] = route
    result["reason"] = reason
    return result


def evaluate_ticket(ticket: Any, provider: Any) -> Dict[str, Any]:
    """Evaluate one synthetic ticket without permitting an external action."""

    result = _base_result(ticket)
    issues = _validation_issues(ticket)
    if issues:
        result["validation_issues"] = issues
        return result

    intent = ticket["intent"].strip().lower()
    message = ticket["message"].lower()
    context = ticket["context"]

    if any(marker in message for marker in INJECTION_MARKERS):
        return _finish(result, "escalate", "prompt_injection_detected")
    if context.get("policy_conflict") is True:
        return _finish(result, "escalate", "policy_conflict")
    if intent in HIGH_RISK_INTENTS:
        return _finish(result, "escalate", "discretionary_or_high_risk_intent")
    if intent in ADMIN_ACTION_INTENTS:
        return _finish(result, "action", "admin_action_requires_human")
    if intent not in DRAFT_INTENTS:
        return _finish(result, "escalate", "unsupported_intent")
    if intent == "wismo" and (
        not context.get("order_id") or not context.get("tracking_status")
    ):
        return _finish(result, "escalate", "missing_required_context")

    try:
        provider_output = provider.generate(deepcopy(ticket))
    except TimeoutError:
        return _finish(result, "escalate", "provider_failure")
    except Exception:
        # Provider details can contain credentials or request content. The
        # public decision record deliberately exposes only the safe category.
        return _finish(result, "escalate", "provider_failure")

    if not isinstance(provider_output, dict):
        return _finish(result, "escalate", "malformed_provider_output")

    draft = provider_output.get("draft")
    citations = provider_output.get("citations")
    confidence = provider_output.get("confidence")
    if (
        not isinstance(draft, str)
        or not draft.strip()
        or not isinstance(citations, list)
        or not citations
        or not all(isinstance(item, str) for item in citations)
        or not isinstance(confidence, (int, float))
    ):
        return _finish(result, "escalate", "malformed_provider_output")

    approved_sources = set(context["approved_source_ids"])
    if not set(citations).issubset(approved_sources):
        return _finish(result, "escalate", "ungrounded_provider_output")
    if float(confidence) < MINIMUM_DRAFT_CONFIDENCE:
        result["confidence"] = float(confidence)
        return _finish(result, "escalate", "low_confidence")

    result.update(
        {
            "route": "draft",
            "reason": "grounded_draft_ready_for_review",
            "draft": draft.strip(),
            "citations": citations,
            "confidence": float(confidence),
        }
    )
    return result


def record_human_review(
    decision: Dict[str, Any], status: str, note: str
) -> Dict[str, Any]:
    """Record review state while keeping the offline engine send-incapable."""

    if status not in {"approved", "rejected"}:
        raise ValueError("status must be approved or rejected")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("a non-empty review note is required")

    reviewed = deepcopy(decision)
    reviewed["human_review_status"] = status
    reviewed["human_review_note"] = note.strip()
    reviewed["automatic_send_allowed"] = False
    if status == "approved" and reviewed.get("route") == "draft":
        reviewed["external_action_state"] = "ready_for_authorized_human_send"
    else:
        reviewed["external_action_state"] = "blocked"
    return reviewed
