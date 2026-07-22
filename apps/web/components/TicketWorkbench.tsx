"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  createHttpSupportApi,
  type CreateTicket,
  type Evaluation,
  type SupportApi,
  type Ticket,
} from "@/lib/api";


type Props = {
  api?: SupportApi;
};

const initialForm = {
  intent: "wismo",
  message: "Where is my fictional order?",
  orderId: "ORDER-DEMO-001",
  trackingStatus: "in_transit",
  providerMode: "success" as CreateTicket["provider_mode"],
};


function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected API error";
}


function decisionTitle(decision: Evaluation): string {
  if (decision.route === "draft") return "Review-only draft";
  if (decision.route === "action") return "Human-owned action";
  return "Human escalation";
}


function humanizeCode(value: string): string {
  return value.replaceAll("_", " ");
}


export function TicketWorkbench({ api: suppliedApi }: Props) {
  const fallbackApi = useMemo(() => createHttpSupportApi(), []);
  const api = suppliedApi ?? fallbackApi;
  const [tickets, setTickets] = useState<Ticket[] | null>(null);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [evaluatingId, setEvaluatingId] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [decision, setDecision] = useState<Evaluation | null>(null);
  const [form, setForm] = useState(initialForm);

  const loadQueue = useCallback(async () => {
    setQueueError(null);
    setTickets(null);
    try {
      const result = await api.listTickets();
      setTickets(result.items);
    } catch (error) {
      setQueueError(errorMessage(error));
    }
  }, [api]);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  async function createTicket(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setActionError(null);
    const externalId = `T-DEMO-${Date.now()}`;
    try {
      const created = await api.createTicket({
        external_id: externalId,
        intent: form.intent,
        message: form.message,
        order_id: form.orderId,
        tracking_status: form.trackingStatus,
        approved_source_ids: ["policy-shipping-v1", form.orderId.toLowerCase()],
        policy_conflict: false,
        provider_mode: form.providerMode,
      });
      setTickets((current) => [created, ...(current ?? [])]);
      setDecision(null);
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setCreating(false);
    }
  }

  async function evaluateTicket(ticket: Ticket) {
    setEvaluatingId(ticket.id);
    setActionError(null);
    try {
      const result = await api.evaluateTicket(ticket.id);
      setDecision(result);
      setTickets((current) =>
        current?.map((item) =>
          item.id === ticket.id ? { ...item, status: "evaluated" } : item,
        ) ?? [],
      );
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setEvaluatingId(null);
    }
  }

  async function review(status: "approved" | "rejected") {
    if (!decision) return;
    setReviewing(true);
    setActionError(null);
    try {
      const result = await api.reviewEvaluation(decision.id, {
        status,
        note: `Synthetic ${status} review recorded in the local workbench.`,
      });
      setDecision(result);
    } catch (error) {
      setActionError(errorMessage(error));
    } finally {
      setReviewing(false);
    }
  }

  return (
    <main className="workbench">
      <header className="masthead">
        <div>
          <p className="eyebrow">Independent engineering proof · v0.3</p>
          <h1>Support readiness workbench</h1>
          <p className="lede">
            A real local workflow for testing whether a synthetic support ticket
            can become a grounded draft—or must stay with a person.
          </p>
        </div>
        <div className="system-boundary" aria-label="System boundary">
          <strong>No automatic send</strong>
          <span>Recorded provider · synthetic data · human review</span>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className="intake-panel" aria-labelledby="intake-title">
          <div className="section-heading">
            <span className="section-index">01</span>
            <div>
              <p className="kicker">Intake</p>
              <h2 id="intake-title">Create a test case</h2>
            </div>
          </div>
          <form onSubmit={createTicket}>
            <label>
              Intent
              <select
                value={form.intent}
                onChange={(event) => setForm({ ...form, intent: event.target.value })}
              >
                <option value="wismo">Where is my order?</option>
                <option value="return_policy">Return policy</option>
                <option value="eligible_return">Eligible return action</option>
                <option value="damaged_item">Damaged item exception</option>
              </select>
            </label>
            <label>
              Synthetic message
              <textarea
                value={form.message}
                onChange={(event) => setForm({ ...form, message: event.target.value })}
                rows={4}
                maxLength={2000}
                required
              />
            </label>
            <div className="field-pair">
              <label>
                Order ID
                <input
                  value={form.orderId}
                  onChange={(event) => setForm({ ...form, orderId: event.target.value })}
                  required
                />
              </label>
              <label>
                Tracking
                <select
                  value={form.trackingStatus}
                  onChange={(event) =>
                    setForm({ ...form, trackingStatus: event.target.value })
                  }
                >
                  <option value="in_transit">In transit</option>
                  <option value="delivered">Delivered</option>
                  <option value="delayed">Delayed</option>
                </select>
              </label>
            </div>
            <label>
              Provider fixture
              <select
                value={form.providerMode}
                onChange={(event) =>
                  setForm({
                    ...form,
                    providerMode: event.target.value as CreateTicket["provider_mode"],
                  })
                }
              >
                <option value="success">Grounded output</option>
                <option value="timeout">Timeout</option>
                <option value="low_confidence">Low confidence</option>
                <option value="bad_citation">Unapproved citation</option>
              </select>
            </label>
            <button className="primary-action" type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create synthetic ticket"}
            </button>
          </form>
          <p className="boundary-note">
            The form writes to the local relational store. It does not create a
            ticket in Gorgias, Shopify, email, or any customer system.
          </p>
        </aside>

        <section className="queue-panel" aria-labelledby="queue-title">
          <div className="queue-header">
            <div className="section-heading">
              <span className="section-index">02</span>
              <div>
                <p className="kicker">Operator queue</p>
                <h2 id="queue-title">Evidence review</h2>
              </div>
            </div>
            <span className="queue-count">
              {tickets === null ? "—" : String(tickets.length).padStart(2, "0")} cases
            </span>
          </div>

          {queueError ? (
            <div className="state-panel state-error" role="alert">
              <strong>Queue unavailable</strong>
              <span>{queueError}</span>
              <button type="button" onClick={() => void loadQueue()}>
                Retry queue
              </button>
            </div>
          ) : tickets === null ? (
            <div className="state-panel" role="status">Loading review queue…</div>
          ) : tickets.length === 0 ? (
            <div className="state-panel state-empty">
              <strong>No tickets yet</strong>
              <span>Create one synthetic case from the intake panel.</span>
            </div>
          ) : (
            <div className="ticket-table" role="list" aria-label="Synthetic tickets">
              <div className="ticket-table-head" aria-hidden="true">
                <span>Case</span><span>Intent</span><span>State</span><span>Decision</span>
              </div>
              {tickets.map((ticket) => (
                <article className="ticket-row" role="listitem" key={ticket.id}>
                  <div>
                    <strong>{ticket.external_id}</strong>
                    <span>{ticket.message}</span>
                  </div>
                  <code>{ticket.intent}</code>
                  <span className={`status status-${ticket.status}`}>{ticket.status}</span>
                  <button
                    type="button"
                    onClick={() => void evaluateTicket(ticket)}
                    disabled={evaluatingId === ticket.id}
                    aria-label={`Evaluate ${ticket.external_id}`}
                  >
                    {evaluatingId === ticket.id ? "Evaluating…" : "Evaluate"}
                  </button>
                </article>
              ))}
            </div>
          )}

          {actionError ? <p className="inline-error" role="alert">{actionError}</p> : null}

          <section className="decision-panel" aria-labelledby="decision-title">
            <div className="section-heading compact">
              <span className="section-index">03</span>
              <div>
                <p className="kicker">Decision record</p>
                <h2 id="decision-title">
                  {decision ? decisionTitle(decision) : "Awaiting evaluation"}
                </h2>
              </div>
            </div>
            {!decision ? (
              <p className="decision-placeholder">
                Run one queue item to expose the route, reason, citations, latency,
                and human-review boundary.
              </p>
            ) : (
              <div className="decision-content">
                <div className="decision-summary">
                  <p>{decision.draft ?? "No draft was produced for this case."}</p>
                  <span className={`route route-${decision.route}`}>{decision.route}</span>
                </div>
                <dl className="evidence-grid">
                  <div><dt>Reason</dt><dd title={decision.reason}>{humanizeCode(decision.reason)}</dd></div>
                  <div><dt>Confidence</dt><dd>{decision.confidence ?? "Not scored"}</dd></div>
                  <div><dt>Latency</dt><dd>{decision.latency_ms.toFixed(1)} ms</dd></div>
                  <div><dt>Review</dt><dd>{decision.human_review_status}</dd></div>
                  <div><dt>External action</dt><dd>{decision.external_action_state}</dd></div>
                  <div><dt>Automatic sends</dt><dd>0 — unavailable by design</dd></div>
                </dl>
                <div className="citations">
                  <span>Citations</span>
                  {decision.citations.length ? (
                    <ul>{decision.citations.map((item) => <li key={item}>{item}</li>)}</ul>
                  ) : (
                    <p>None; this case remains with a human.</p>
                  )}
                </div>
                <div className="review-actions" aria-label="Human review decision">
                  <button
                    type="button"
                    onClick={() => void review("approved")}
                    disabled={reviewing || decision.route !== "draft"}
                  >
                    Record approval
                  </button>
                  <button
                    type="button"
                    onClick={() => void review("rejected")}
                    disabled={reviewing}
                  >
                    Record rejection
                  </button>
                  <p>Approval records readiness only; no external action follows.</p>
                </div>
              </div>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}
