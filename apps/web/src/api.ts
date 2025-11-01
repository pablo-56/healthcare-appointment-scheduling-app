export const API = (import.meta as any).env.VITE_API_BASE || 'http://localhost:8000';

export async function triageAndSlots(reason: string) {
    const r = await fetch(`${API}/v1/agents/scheduling/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Purpose-Of-Use': 'OPERATIONS' },
        body: JSON.stringify({ reason }),
    });
    if (!r.ok) throw new Error(`intake failed ${r.status}`);
    return r.json();
}

export async function bookAppointment(input: {
    patient_email?: string;
    reason: string;
    start: string;
    end: string;
    slot_id?: string;
}) {
    const r = await fetch(`${API}/v1/appointments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Purpose-Of-Use': 'TREATMENT' },
        body: JSON.stringify({ source_channel: 'web', ...input }),
    });
    if (!r.ok) throw new Error(`book failed ${r.status}`);
    return r.json();
}


export async function fetchAdminTasks() {
  const r = await fetch(import.meta.env.VITE_API_URL + "/v1/admin/tasks");
  if (!r.ok) throw new Error("failed to fetch tasks");
  return r.json();
}

export async function fetchEligibility(appointmentId: number) {
  const u = new URL(import.meta.env.VITE_API_URL + "/v1/admin/billing/eligibility");
  u.searchParams.set("appointment_id", String(appointmentId));
  const r = await fetch(u.toString());
  if (!r.ok) throw new Error("failed to fetch eligibility");
  return r.json();
}

// apps/web/src/api.ts (append)
export async function getPrechart(appointmentId: number) {
  const r = await fetch(`/v1/prechart/${appointmentId}`, {
    headers: { "X-Purpose-Of-Use": "OPERATIONS" },
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

// apps/web/src/api.ts
export async function postTask(task: any) {
  const res = await fetch("/v1/tasks", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Purpose-Of-Use": "OPERATIONS",  // <-- critical
    },
    body: JSON.stringify(task),
  });
  if (!res.ok) throw new Error(`POST /v1/tasks failed: ${res.status}`);
  return res.json();
}

export async function listTasks(q: Record<string,string|number> = {}) {
  const url = "/v1/tasks?" + new URLSearchParams(q as any).toString();
  const res = await fetch(url, {
    headers: { "X-Purpose-Of-Use": "OPERATIONS" },
  });
  if (!res.ok) throw new Error(`GET /v1/tasks failed: ${res.status}`);
  return res.json();
}
