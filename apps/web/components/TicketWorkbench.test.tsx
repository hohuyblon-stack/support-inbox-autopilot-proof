import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TicketWorkbench } from "./TicketWorkbench";
import type { SupportApi, Ticket } from "@/lib/api";


const ticket: Ticket = {
  id: "ticket-1",
  external_id: "T-DEMO-001",
  intent: "wismo",
  message: "Where is my fictional order?",
  status: "pending",
  created_at: "2026-07-22T07:00:00Z",
};


function api(overrides: Partial<SupportApi> = {}): SupportApi {
  return {
    listTickets: vi.fn().mockResolvedValue({ items: [], next_cursor: null }),
    createTicket: vi.fn().mockResolvedValue(ticket),
    evaluateTicket: vi.fn().mockResolvedValue({
      id: "evaluation-1",
      ticket_id: ticket.id,
      route: "draft",
      reason: "grounded_draft_ready_for_review",
      draft: "Your fictional order is in transit.",
      citations: ["policy-shipping-v1", "order-demo-001"],
      confidence: 0.91,
      automatic_send_allowed: false,
      human_review_status: "pending",
      external_action_state: "blocked",
      latency_ms: 12.5,
    }),
    reviewEvaluation: vi.fn(),
    ...overrides,
  };
}


describe("TicketWorkbench", () => {
  it("renders a truthful empty state after loading", async () => {
    render(<TicketWorkbench api={api()} />);

    expect(screen.getByText("Loading review queue…")).toBeInTheDocument();
    expect(await screen.findByText("No tickets yet")).toBeInTheDocument();
  });

  it("exposes a retryable error state", async () => {
    const supportApi = api({
      listTickets: vi
        .fn()
        .mockRejectedValueOnce(new Error("API unavailable"))
        .mockResolvedValueOnce({ items: [], next_cursor: null }),
    });
    render(<TicketWorkbench api={supportApi} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("API unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Retry queue" }));

    expect(await screen.findByText("No tickets yet")).toBeInTheDocument();
    expect(supportApi.listTickets).toHaveBeenCalledTimes(2);
  });

  it("creates and evaluates a ticket without exposing an automatic-send action", async () => {
    const supportApi = api();
    render(<TicketWorkbench api={supportApi} />);
    await screen.findByText("No tickets yet");

    fireEvent.click(screen.getByRole("button", { name: "Create synthetic ticket" }));
    expect(await screen.findByText("T-DEMO-001")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Evaluate T-DEMO-001" }));
    expect(await screen.findByText("Review-only draft")).toBeInTheDocument();
    expect(screen.getByText("Your fictional order is in transit.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /send/i })).not.toBeInTheDocument();
    await waitFor(() => expect(supportApi.evaluateTicket).toHaveBeenCalledWith(ticket.id));
  });
});
