export type Role = "user" | "assistant";
export type Message = { role: Role; content: string; artifacts?: Artifacts | null };
export type Artifacts = {
  image_base64?: string | null;
  sources?: { source_file?: string; section?: string; page?: number }[];
  web_image?: { image_url: string; source_url: string; caption: string } | null;
};

const API_URL = import.meta.env.VITE_BACKEND_API_URL ?? (import.meta.env.DEV ? "http://127.0.0.1:8001" : "/api");

export class ApiError extends Error {
  constructor(public code: string, message: string) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Critical React -> FastAPI connection. Every request receives a trace ID in backend.log.
  const response = await fetch(`${API_URL}${path}`, { ...init, headers: { "X-Request-ID": crypto.randomUUID(), ...(init?.headers ?? {}) } });
  const body = await response.json();
  if (!response.ok) throw new ApiError(body.code ?? "REQUEST_FAILED", body.message ?? "Request failed.");
  return body as T;
}

export function reportClientEvent(event: string, detail?: string) {
  // Diagnostics are deliberately fire-and-forget so logging cannot break the UI.
  return request<{ status: string }>("/client-events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event, detail }),
  }).catch(() => undefined);
}

export function sendChat(question: string, conversationId: string | null, activeSourceFile: string | null) {
  return request<{ answer: string; artifacts?: Artifacts; conversation_id: string }>("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId, active_source_file: activeSourceFile }),
  });
}

export function fetchConversation(conversationId: string) {
  return request<{ id: string; messages: Message[] }>(`/conversations/${conversationId}`);
}

export function uploadDocument(file: File) {
  const form = new FormData(); form.append("file", file);
  return request<{ filename: string; chunks_added: number }>("/documents", { method: "POST", body: form });
}
