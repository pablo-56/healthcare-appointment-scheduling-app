// apps/web/src/lib/fetcher.ts
type ApiInit = RequestInit & { pou?: "OPERATIONS" | "TREATMENT" | "PAYMENT" | string };

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// Default PoU by HTTP method (override by passing init.pou)
const DEFAULT_POU_BY_METHOD: Record<string, string> = {
  GET: "OPERATIONS",
  HEAD: "OPERATIONS",
  OPTIONS: "OPERATIONS",
  POST: "TREATMENT",
  PUT: "TREATMENT",
  PATCH: "TREATMENT",
  DELETE: "TREATMENT",
};

export async function api(path: string, init: ApiInit = {}) {
  const method = (init.method || "GET").toUpperCase();
  const headers: Record<string, string> = { ...(init.headers as Record<string, string> | undefined) };

  // Always send PoU (default by method unless explicitly provided)
  const pou = init.pou || DEFAULT_POU_BY_METHOD[method] || "OPERATIONS";
  headers["X-Purpose-Of-Use"] = pou;

  // Ensure JSON header when sending a body
  if (init.body && !("Content-Type" in headers)) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    method,
    headers,
    credentials: "include", // send dev-session cookies from the API origin
  });

  const ctype = res.headers.get("content-type") || "";
  const data = ctype.includes("application/json")
    ? await res.json().catch(() => null)
    : await res.text();

  if (!res.ok) {
    // surface API error body in the UI
    throw new Error(data ? (typeof data === "string" ? data : JSON.stringify(data)) : res.statusText);
  }
  return data;
}
