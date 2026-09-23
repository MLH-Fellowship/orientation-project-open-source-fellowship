// Thin wrapper around fetch for talking to the FastAPI backend.
// Extend this as new endpoints are added (pagination, rename, delete...).

const BASE = "/api";

function extractErrorMessage(data, status) {
  if (typeof data?.error?.message === "string") {
    return data.error.message;
  }
  if (data && typeof data.detail === "string") {
    return data.detail;
  }
  if (data && Array.isArray(data.detail) && data.detail[0]?.msg) {
    return data.detail[0].msg;
  }
  return `Request failed with status ${status}`;
}

async function parseJsonResponse(res) {
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const error = new Error(extractErrorMessage(data, res.status));
    error.status = res.status;
    throw error;
  }
  return data;
}

export async function createConversation(title) {
  const res = await fetch(`${BASE}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return parseJsonResponse(res);
}

export async function listConversations({ limit, offset } = {}) {
  const params = new URLSearchParams();
  if (limit !== undefined) params.set("limit", limit);
  if (offset !== undefined) params.set("offset", offset);
  const query = params.toString();
  const res = await fetch(`${BASE}/conversations${query ? `?${query}` : ""}`);
  return parseJsonResponse(res);
}

export async function getConversation(id) {
  const res = await fetch(`${BASE}/conversations/${id}`);
  return parseJsonResponse(res);
}

export async function sendMessage(conversationId, content) {
  const res = await fetch(`${BASE}/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  return parseJsonResponse(res);
}

export async function streamMessage(conversationId, content, { signal, onToken }) {
  const res = await fetch(`${BASE}/conversations/${conversationId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ content }),
    signal,
  });
  if (!res.ok) await parseJsonResponse(res);
  if (!res.body) throw new Error("Streaming is unavailable in this browser.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      // Network chunks can split UTF-8 characters, lines, and entire events.
      let boundary;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const frame = buffer.slice(0, boundary.index);
        buffer = buffer.slice(boundary.index + boundary[0].length);
        let event = "message";
        const data = [];
        for (const line of frame.split(/\r?\n/)) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
        }
        if (!data.length || !["token", "done", "error"].includes(event)) continue;
        const payload = JSON.parse(data.join("\n"));
        if (event === "error") {
          throw new Error(payload.error?.message || "Could not generate reply");
        }
        if (event === "done") {
          if (!payload?.id || payload.role !== "assistant" || typeof payload.content !== "string") {
            throw new Error("The server returned an invalid reply.");
          }
          return payload;
        }
        if (typeof payload?.content !== "string") {
          throw new Error("The server returned an invalid reply chunk.");
        }
        onToken(payload.content);
      }
      if (done) throw new Error("The reply was interrupted. Please try again.");
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

export async function renameConversation(id, title) {
  const res = await fetch(`${BASE}/conversations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return parseJsonResponse(res);
}

export async function deleteConversation(id) {
  const res = await fetch(`${BASE}/conversations/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(extractErrorMessage(data, res.status));
  }
}
