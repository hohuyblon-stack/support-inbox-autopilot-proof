export type Ticket = {
  id: string;
  external_id: string;
  intent: string;
  message: string;
  status: "pending" | "evaluated";
  created_at: string;
};

export type TicketList = {
  items: Ticket[];
  next_cursor: string | null;
};

export type CreateTicket = {
  external_id: string;
  intent: string;
  message: string;
  order_id: string;
  tracking_status: string;
  approved_source_ids: string[];
  policy_conflict: boolean;
  provider_mode: "success" | "timeout" | "low_confidence" | "bad_citation";
};

export type Evaluation = {
  id: string;
  ticket_id: string;
  route: "draft" | "action" | "escalate";
  reason: string;
  draft: string | null;
  citations: string[];
  confidence: number | null;
  automatic_send_allowed: false;
  human_review_status: "pending" | "approved" | "rejected";
  external_action_state: "blocked" | "ready_for_authorized_human_send";
  latency_ms: number;
};

export type Review = {
  status: "approved" | "rejected";
  note: string;
};

export interface SupportApi {
  listTickets(): Promise<TicketList>;
  createTicket(payload: CreateTicket): Promise<Ticket>;
  evaluateTicket(ticketId: string): Promise<Evaluation>;
  reviewEvaluation(evaluationId: string, review: Review): Promise<Evaluation>;
}

type ApiErrorBody = {
  detail?: string | { code?: string };
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const message =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.code ?? `Request failed (${response.status})`;
    throw new Error(message.replaceAll("_", " "));
  }
  return (await response.json()) as T;
}

export function createHttpSupportApi(
  baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000",
): SupportApi {
  const base = baseUrl.replace(/\/$/, "");
  return {
    listTickets: () => request<TicketList>(`${base}/api/v1/tickets?limit=50`),
    createTicket: (payload) =>
      request<Ticket>(`${base}/api/v1/tickets`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    evaluateTicket: (ticketId) =>
      request<Evaluation>(`${base}/api/v1/tickets/${ticketId}/evaluate`, {
        method: "POST",
      }),
    reviewEvaluation: (evaluationId, review) =>
      request<Evaluation>(`${base}/api/v1/evaluations/${evaluationId}/review`, {
        method: "POST",
        body: JSON.stringify(review),
      }),
  };
}
