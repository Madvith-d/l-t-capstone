const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = Number(process.env.NEXT_PUBLIC_REQUEST_TIMEOUT_MS ?? 45000);

export type Source = { document_id: string; title: string; page?: number; section?: string; source: string; score?: number };
export type ChatResult = { conversation_id: string; intent: string; answer: string; sources: Source[]; confidence: number; tool_results: Record<string, unknown>[]; graph_route: string[] };
export type Session = { id?: string; session_date: string; subject: string; topic: string; duration_minutes: number; preferred_time?: string; status: string };
export type Subject = { name: string; topics: string[]; difficulty: number };
export type Plan = { id: string; title: string; exam_date: string; available_hours_per_day: number; subjects: Subject[]; version: number; sessions: Session[] };
export type Document = { id: string; title: string; category?: string; department?: string; academic_year?: string; source: string; status: string };
export type Message = { id: string; role: string; content: string; sources: Source[] };
export type Conversation = { id: string; title: string; updated_at: string; messages?: Message[] };
export type DemoStatus = { enabled: boolean; label: string; questions: string[] };

export class ApiError extends Error {
  constructor(message: string, public status = 0, public code = "request_failed") { super(message); }
}

function userId(): string {
  if (typeof window === "undefined") return "server-render-session";
  const key = "academic-agent-user-id";
  let value = window.localStorage.getItem(key) ?? window.localStorage.getItem("northstar-user-id");
  if (!value) value = crypto.randomUUID();
  window.localStorage.setItem(key, value);
  return value;
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function assertArray(value: unknown, label: string): asserts value is unknown[] {
  if (!Array.isArray(value)) throw new ApiError(`Invalid ${label} response from the server.`, 502, "invalid_response");
}

function parseChat(value: unknown): ChatResult {
  if (!object(value) || typeof value.conversation_id !== "string" || typeof value.answer !== "string" || !Array.isArray(value.sources) || !Array.isArray(value.graph_route)) {
    throw new ApiError("Invalid chat response from the server.", 502, "invalid_response");
  }
  return value as unknown as ChatResult;
}

function parsePlan(value: unknown): Plan {
  if (!object(value) || typeof value.id !== "string" || !Array.isArray(value.sessions) || !Array.isArray(value.subjects)) {
    throw new ApiError("Invalid study-plan response from the server.", 502, "invalid_response");
  }
  return value as unknown as Plan;
}

function parseDocument(value: unknown): Document {
  if (!object(value) || typeof value.id !== "string" || typeof value.title !== "string" || typeof value.status !== "string") {
    throw new ApiError("Invalid document response from the server.", 502, "invalid_response");
  }
  return value as unknown as Document;
}

function parseDemoStatus(value: unknown): DemoStatus {
  if (!object(value) || typeof value.enabled !== "boolean" || typeof value.label !== "string" || !Array.isArray(value.questions)) {
    throw new ApiError("Invalid demo-mode response from the server.", 502, "invalid_response");
  }
  return value as unknown as DemoStatus;
}

function parseConversation(value: unknown): Conversation {
  if (!object(value) || typeof value.id !== "string" || typeof value.title !== "string") {
    throw new ApiError("Invalid conversation response from the server.", 502, "invalid_response");
  }
  return value as unknown as Conversation;
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const isFormData = init?.body instanceof FormData;
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        "X-User-ID": userId(),
        ...init?.headers,
      },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = object(body) ? body.detail : undefined;
      const message = typeof detail === "string" ? detail : object(detail) && typeof detail.message === "string" ? detail.message : "The request failed.";
      const code = object(body) && typeof body.error === "string" ? body.error : object(detail) && typeof detail.code === "string" ? detail.code : "request_failed";
      throw new ApiError(message, response.status, code);
    }
    return body;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") throw new ApiError("The request timed out. Please try again.", 0, "timeout");
    throw new ApiError("The backend could not be reached.", 0, "backend_unavailable");
  } finally {
    window.clearTimeout(timeout);
  }
}

export const api = {
  demoStatus: async () => parseDemoStatus(await request("/api/demo")),
  chat: async (question: string, conversationId?: string, planId?: string) => parseChat(await request("/api/chat", { method: "POST", body: JSON.stringify({ question, conversation_id: conversationId, plan_id: planId }) })),
  conversations: async () => { const value = await request("/api/conversations"); assertArray(value, "conversation list"); return value.map(parseConversation); },
  conversation: async (id: string) => parseConversation(await request(`/api/conversations/${id}`)),
  plans: async () => { const value = await request("/api/plans"); assertArray(value, "plan list"); return value.map(parsePlan); },
  createPlan: async (payload: object) => parsePlan(await request("/api/plans", { method: "POST", body: JSON.stringify(payload) })),
  modifyPlan: async (id: string, instruction: string) => parsePlan(await request(`/api/plans/${id}`, { method: "PATCH", body: JSON.stringify({ instruction }) })),
  documents: async () => { const value = await request("/api/documents"); assertArray(value, "document list"); return value.map(parseDocument); },
  ingestDocument: async (form: FormData) => parseDocument(await request("/api/documents/ingest", { method: "POST", body: form })),
};
