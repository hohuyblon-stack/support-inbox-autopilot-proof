import asyncio
from pathlib import Path

import httpx
import pytest

from apps.api.app.main import create_app
from apps.api.app.providers import DeterministicContextProvider


def ticket_payload(**overrides):
    payload = {
        "external_id": "T-DEMO-001",
        "intent": "wismo",
        "message": "Where is my fictional order?",
        "order_id": "ORDER-DEMO-001",
        "tracking_status": "in_transit",
        "approved_source_ids": ["policy-shipping-v1", "order-demo-001"],
        "policy_conflict": False,
        "provider_mode": "success",
    }
    payload.update(overrides)
    return payload


class FailingContextProvider:
    async def fetch_order(self, order_id, tracking_status, mode):
        raise RuntimeError("synthetic upstream failure with private details")

    async def fetch_policy(self, source_ids, mode):
        raise RuntimeError("synthetic upstream failure with private details")


@pytest.fixture
async def client(tmp_path: Path):
    app = create_app(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.sqlite3'}",
        auto_create_schema=True,
        context_provider=DeterministicContextProvider(delay_seconds=0),
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as api_client:
            yield api_client


@pytest.mark.asyncio
async def test_complete_operator_journey_never_sends_automatically(client):
    created = await client.post("/api/v1/tickets", json=ticket_payload())
    assert created.status_code == 201, created.text
    ticket = created.json()
    assert ticket["status"] == "pending"

    listed = await client.get("/api/v1/tickets?limit=10")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["external_id"] == "T-DEMO-001"

    evaluated = await client.post(f"/api/v1/tickets/{ticket['id']}/evaluate")
    assert evaluated.status_code == 200, evaluated.text
    decision = evaluated.json()
    assert decision["route"] == "draft"
    assert decision["reason"] == "grounded_draft_ready_for_review"
    assert decision["draft"] == "Your fictional order status is in transit."
    assert decision["automatic_send_allowed"] is False
    assert decision["human_review_status"] == "pending"
    assert set(decision["citations"]) <= {
        "policy-shipping-v1",
        "order-demo-001",
    }

    reviewed = await client.post(
        f"/api/v1/evaluations/{decision['id']}/review",
        json={"status": "approved", "note": "Synthetic demo reviewed."},
    )
    assert reviewed.status_code == 200, reviewed.text
    review = reviewed.json()
    assert review["human_review_status"] == "approved"
    assert review["automatic_send_allowed"] is False
    assert review["external_action_state"] == "ready_for_authorized_human_send"

    metrics = await client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    assert metrics.json() == {
        "tickets_total": 1,
        "evaluations_total": 1,
        "routes": {"draft": 1},
        "automatic_sends": 0,
    }


@pytest.mark.asyncio
async def test_duplicate_external_id_is_an_explicit_conflict(client):
    first = await client.post("/api/v1/tickets", json=ticket_payload())
    second = await client.post("/api/v1/tickets", json=ticket_payload())

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "external_id_conflict"


@pytest.mark.asyncio
async def test_provider_timeout_is_recorded_as_a_human_escalation(client):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(
            external_id="T-DEMO-TIMEOUT",
            provider_mode="timeout",
        ),
    )
    ticket = created.json()

    evaluated = await client.post(f"/api/v1/tickets/{ticket['id']}/evaluate")

    assert evaluated.status_code == 200
    decision = evaluated.json()
    assert decision["route"] == "escalate"
    assert decision["reason"] == "provider_failure"
    assert decision["automatic_send_allowed"] is False
    assert decision["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_unexpected_provider_failure_degrades_to_safe_escalation(tmp_path: Path):
    app = create_app(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'failure.sqlite3'}",
        auto_create_schema=True,
        context_provider=FailingContextProvider(),
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as api_client:
            created = await api_client.post(
                "/api/v1/tickets",
                json=ticket_payload(external_id="T-DEMO-PROVIDER-FAILURE"),
            )
            evaluated = await api_client.post(
                f"/api/v1/tickets/{created.json()['id']}/evaluate"
            )

    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["route"] == "escalate"
    assert evaluated.json()["reason"] == "provider_failure"
    assert "private details" not in evaluated.text


@pytest.mark.asyncio
async def test_approving_a_high_risk_route_cannot_unlock_external_action(client):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(
            external_id="T-DEMO-HIGH-RISK",
            intent="chargeback",
        ),
    )
    evaluated = await client.post(
        f"/api/v1/tickets/{created.json()['id']}/evaluate"
    )
    reviewed = await client.post(
        f"/api/v1/evaluations/{evaluated.json()['id']}/review",
        json={"status": "approved", "note": "Escalation acknowledged."},
    )

    assert evaluated.json()["route"] == "escalate"
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["human_review_status"] == "approved"
    assert reviewed.json()["external_action_state"] == "blocked"
    assert reviewed.json()["automatic_send_allowed"] is False


@pytest.mark.asyncio
async def test_validation_and_bounded_pagination_are_api_contracts(client):
    invalid = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(message="", approved_source_ids=[]),
    )
    assert invalid.status_code == 422

    too_large = await client.get("/api/v1/tickets?limit=101")
    assert too_large.status_code == 422


@pytest.mark.asyncio
async def test_health_and_readiness_are_distinct(client):
    health = await client.get("/healthz")
    readiness = await client.get("/readyz")

    assert health.json() == {"status": "ok"}
    assert readiness.json() == {"database": "ready", "status": "ready"}


@pytest.mark.asyncio
async def test_repeated_evaluation_is_idempotent(client):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(external_id="T-DEMO-IDEMPOTENT"),
    )
    ticket = created.json()

    first = await client.post(f"/api/v1/tickets/{ticket['id']}/evaluate")
    second = await client.post(f"/api/v1/tickets/{ticket['id']}/evaluate")
    metrics = await client.get("/api/v1/metrics")

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["id"] == first.json()["id"]
    assert metrics.json()["evaluations_total"] == 1


@pytest.mark.asyncio
async def test_concurrent_evaluation_retries_resolve_to_one_result(client):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(external_id="T-DEMO-CONCURRENT-IDEMPOTENT"),
    )
    ticket_id = created.json()["id"]

    first, second = await asyncio.gather(
        client.post(f"/api/v1/tickets/{ticket_id}/evaluate"),
        client.post(f"/api/v1/tickets/{ticket_id}/evaluate"),
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_duplicate_context_source_is_stored_once(client):
    created = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(
            external_id="T-DEMO-DUPLICATE-CITATION",
            order_id="policy-shipping-v1",
            approved_source_ids=["policy-shipping-v1"],
        ),
    )

    evaluated = await client.post(
        f"/api/v1/tickets/{created.json()['id']}/evaluate"
    )

    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["citations"] == ["policy-shipping-v1"]


@pytest.mark.asyncio
async def test_cursor_must_belong_to_the_requested_status_filter(client):
    pending = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(external_id="T-DEMO-PENDING-CURSOR"),
    )
    evaluated = await client.post(
        "/api/v1/tickets",
        json=ticket_payload(external_id="T-DEMO-EVALUATED-CURSOR"),
    )
    await client.post(f"/api/v1/tickets/{evaluated.json()['id']}/evaluate")

    response = await client.get(
        "/api/v1/tickets",
        params={"status": "evaluated", "cursor": pending.json()["id"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "invalid_cursor"
