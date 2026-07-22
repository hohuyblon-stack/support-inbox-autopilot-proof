import asyncio
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class DeterministicContextProvider:
    """Local async adapter that models two independent context reads.

    It never creates a network connection. The delay exists to exercise real
    scheduling, cancellation, and timeout behavior with deterministic fixtures.
    """

    delay_seconds: float = 0.02

    async def fetch_order(
        self,
        order_id: str | None,
        tracking_status: str | None,
        mode: str,
    ) -> dict[str, Any]:
        await asyncio.sleep(self.delay_seconds)
        if mode == "timeout":
            raise TimeoutError("recorded order provider timeout")
        return {
            "source_id": (order_id or "order-context-missing").lower(),
            "tracking_status": tracking_status,
        }

    async def fetch_policy(
        self,
        source_ids: Iterable[str],
        mode: str,
    ) -> dict[str, Any]:
        await asyncio.sleep(self.delay_seconds)
        if mode == "timeout":
            raise TimeoutError("recorded policy provider timeout")
        policy_source = next(
            (item for item in source_ids if item.startswith("policy-")),
            next(iter(source_ids), "policy-context-missing"),
        )
        return {
            "source_id": policy_source,
            "summary": "Synthetic policy permits a grounded status draft.",
        }


async def collect_context(
    provider: Any,
    *,
    order_id: str | None,
    tracking_status: str | None,
    approved_source_ids: Iterable[str],
    mode: str,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    async with asyncio.timeout(timeout_seconds):
        order, policy = await asyncio.gather(
            provider.fetch_order(order_id, tracking_status, mode),
            provider.fetch_policy(approved_source_ids, mode),
        )
    return [order, policy]


def provider_output_for(
    context_items: list[dict[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    # Independent adapters can legitimately resolve to the same source. Keep
    # the first occurrence so the persistence uniqueness constraint cannot turn
    # a valid grounded result into a server error.
    citations = list(dict.fromkeys(item["source_id"] for item in context_items))
    if mode == "bad_citation":
        citations = ["unapproved-source"]
    confidence = 0.55 if mode == "low_confidence" else 0.91
    raw_tracking_status = context_items[0].get("tracking_status") or "not available"
    tracking_status = str(raw_tracking_status).replace("_", " ")
    return {
        "draft": f"Your fictional order status is {tracking_status}.",
        "citations": citations,
        "confidence": confidence,
    }
