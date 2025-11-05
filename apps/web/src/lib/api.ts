import { api } from "./fetcher";

function splitIdentity(identity: string) {
  const raw = String(identity || "").trim();
  if (raw.includes("@")) return { email: raw };
  const phone = raw.replace(/\D/g, "");
  return phone ? { phone } : {};
}

export async function sendOtp(identity: string) {
  const payload = splitIdentity(identity);
  if (!payload.email && !payload.phone) throw new Error("Provide email or phone");
  return api("/v1/auth/otp:send", {
    method: "POST",
    body: JSON.stringify(payload),
    pou: "OPERATIONS",
  });
}

export async function verifyOtp(identity: string, code: string) {
  const payload = { ...splitIdentity(identity), code };
  if ((!payload as any).email && !(payload as any).phone) throw new Error("Provide email or phone");
  if (!code) throw new Error("Provide code");
  return api("/v1/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
    pou: "OPERATIONS",
  });
}

export async function bookAppointment(input: {
  patient_id: number;
  start: string;  // ISO8601
  end: string;    // ISO8601
  reason: string;
  source_channel?: string;
  patient_email?: string | null;
}) {
  return api("/v1/appointments/book", {
    method: "POST",
    body: JSON.stringify(input),
    // PoU defaults to TREATMENT for POST in fetcher.ts
  });
}

export async function getEligibility(appointmentId: number) {
  return api(`/v1/admin/billing/eligibility?appointment_id=${appointmentId}`, {
    method: "GET",
    pou: "OPERATIONS",
  });
}

export async function getAppointment(appointmentId: number) {
  // GET uses PoU=OPERATIONS by default in fetcher.ts; explicit is ok too.
  return api(`/v1/appointments/${appointmentId}`, { method: "GET", pou: "OPERATIONS" });
}


export async function complianceGet<T=any>(path: string): Promise<T> {
  return api(path, { method: "GET", pou: "OPERATIONS" });
}

export async function compliancePost<T=any>(path: string, body?: any): Promise<T> {
  return api(path, { method: "POST", body: JSON.stringify(body || {}), pou: "OPERATIONS" });
}

// Simple client-side CSV download for small result sets
export function downloadCsv(filename: string, rows: any[]) {
  const keys = Array.from(rows.reduce<Set<string>>((s, r) => {
    Object.keys(r || {}).forEach(k => s.add(k));
    return s;
  }, new Set<string>()));

  const escape = (v:any) => {
    const s = String(v ?? "");
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };

  const csv = [keys.join(",")]
    .concat(rows.map(r => keys.map(k => escape(r?.[k])).join(",")))
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}