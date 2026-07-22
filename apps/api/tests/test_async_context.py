import asyncio

import pytest

from apps.api.app.providers import collect_context


class RendezvousProvider:
    def __init__(self):
        self.started = 0
        self.both_started = asyncio.Event()

    async def _arrive(self, value):
        self.started += 1
        if self.started == 2:
            self.both_started.set()
        await self.both_started.wait()
        return value

    async def fetch_order(self, order_id, tracking_status, mode):
        return await self._arrive(
            {"source_id": "order-demo-001", "tracking_status": tracking_status}
        )

    async def fetch_policy(self, source_ids, mode):
        return await self._arrive(
            {"source_id": "policy-shipping-v1", "summary": "Synthetic policy"}
        )


class NeverReturningProvider:
    def __init__(self):
        self.cancelled = 0

    async def _wait(self):
        try:
            await asyncio.Event().wait()
        finally:
            self.cancelled += 1

    async def fetch_order(self, order_id, tracking_status, mode):
        await self._wait()

    async def fetch_policy(self, source_ids, mode):
        await self._wait()


@pytest.mark.asyncio
async def test_independent_context_calls_start_concurrently():
    provider = RendezvousProvider()

    result = await asyncio.wait_for(
        collect_context(
            provider,
            order_id="ORDER-DEMO-001",
            tracking_status="in_transit",
            approved_source_ids=["policy-shipping-v1", "order-demo-001"],
            mode="success",
            timeout_seconds=0.2,
        ),
        timeout=0.3,
    )

    assert provider.started == 2
    assert {item["source_id"] for item in result} == {
        "order-demo-001",
        "policy-shipping-v1",
    }


@pytest.mark.asyncio
async def test_timeout_cancels_both_pending_context_reads():
    provider = NeverReturningProvider()

    with pytest.raises(TimeoutError):
        await collect_context(
            provider,
            order_id="ORDER-DEMO-001",
            tracking_status="in_transit",
            approved_source_ids=["policy-shipping-v1", "order-demo-001"],
            mode="success",
            timeout_seconds=0.01,
        )

    assert provider.cancelled == 2
