import { preferences } from "./preferences.js";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

const DEFAULT_ERROR = "Something went wrong. Please try again.";
const NETWORK_ERROR = "Unable to reach the server. Please check that the backend is running.";

export class ApiError extends Error {
  constructor(message, { status = 0, code = "unknown_error", requestId = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

async function request(path, { method = "GET", body, headers = {} } = {}) {
  const accessKey = preferences.getAccessKey();
  const allHeaders = accessKey ? { ...headers, "X-Access-Key": accessKey } : headers;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method, body, headers: allHeaders });
  } catch {
    throw new ApiError(NETWORK_ERROR, { code: "network_error" });
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = data?.error;
    throw new ApiError(error?.message || DEFAULT_ERROR, {
      status: response.status,
      code: error?.code,
      requestId: error?.request_id ?? response.headers.get("X-Request-ID"),
    });
  }
  return data;
}

function sendJson(method, path, payload) {
  return request(path, {
    method,
    body: JSON.stringify(payload),
    headers: { "Content-Type": "application/json" },
  });
}

const EXTENSIONS = { "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/wav": "wav" };

function audioFilename(blob) {
  const type = (blob.type || "").split(";")[0];
  return `recording.${EXTENSIONS[type] || "webm"}`;
}

export const api = {
  getModes: () => request("/api/v1/modes"),
  getConfig: () => request("/api/v1/config"),
  getProviderHealth: () => request("/api/v1/providers/health"),

  transcribe(blob) {
    const form = new FormData();
    form.append("audio", blob, audioFilename(blob));
    return request("/api/v1/transcribe", { method: "POST", body: form });
  },

  chat: ({ conversationId, message, mode, provider, customInstructions }) =>
    sendJson("POST", "/api/v1/chat", {
      conversation_id: conversationId || null,
      message,
      mode,
      provider: provider && provider !== "auto" ? provider : null,
      custom_instructions: customInstructions || null,
    }),

  listConversations: () => request("/api/v1/conversations"),
  getConversation: (id) => request(`/api/v1/conversations/${encodeURIComponent(id)}`),
  deleteConversation: (id) => request(`/api/v1/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }),

  getUserContext: () => request("/api/v1/user/context"),
  saveUserContext: (context) => sendJson("POST", "/api/v1/user/context", context),
  clearUserContext: () => request("/api/v1/user/context", { method: "DELETE" }),
};
