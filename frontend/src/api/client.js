// Thin wrapper around fetch for talking to the FastAPI backend.
// Extend this as new endpoints are added (pagination, rename, delete...).

// In dev this stays "/api" and Vite proxies it to the backend.
// In production VITE_API_BASE points at the deployed API.
const BASE = import.meta.env.VITE_API_BASE || "/api";

export async function createConversation(title) {
  const res = await fetch(`${BASE}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function listConversations({ limit, offset } = {}) {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", limit);
  if (offset !== undefined) params.set("offset", offset);
  const query = params.toString();
  const res = await fetch(`${BASE}/conversations${query ? `?${query}` : ""}`);
  return res.json();
}

export async function getConversation(id) {
  const res = await fetch(`${BASE}/conversations/${id}`);
  return res.json();
}

export async function sendMessage(conversationId, content) {
  const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  return res.json();
}
