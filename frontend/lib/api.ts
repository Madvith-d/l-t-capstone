const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Source = { document_id: string; title: string; page?: number; section?: string; source: string; score?: number };
export type ChatResult = { conversation_id: string; intent: string; answer: string; sources: Source[]; confidence: number };
export type Session = { id?: string; session_date: string; subject: string; topic: string; duration_minutes: number; status: string };
export type Plan = { id: string; title: string; exam_date: string; available_hours_per_day: number; version: number; sessions: Session[] };
export type Document = { id: string; title: string; category?: string; department?: string; academic_year?: string; source: string; status: string };
export type Conversation = { id: string; title: string; updated_at: string; messages: { id: string; role: string; content: string; sources: Source[] }[] };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : body.detail?.message;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json();
}

export const api = {
  chat: (question: string, conversationId?: string) => request<ChatResult>("/api/chat", { method: "POST", body: JSON.stringify({ question, conversation_id: conversationId }) }),
  conversations: () => request<Conversation[]>("/api/conversations"),
  createPlan: (payload: object) => request<Plan>("/api/plans", { method: "POST", body: JSON.stringify(payload) }),
  modifyPlan: (id: string, instruction: string) => request<Plan>(`/api/plans/${id}`, { method: "PATCH", body: JSON.stringify({ instruction }) }),
  documents: () => request<Document[]>("/api/documents"),
};
