// apps/web/src/lib/auth.ts
import { api } from "./fetcher";

export type Role = "PATIENT" | "CLINICIAN" | "OPS" | "ANON";

export async function getMe(): Promise<{ id?: number; email?: string; role: Role }> {
  // No PoU needed here; it’s auth identity. If your middleware enforces,
  // you can add pou: "OPERATIONS" safely.
  return api("/v1/auth/me", { method: "GET" });
}
