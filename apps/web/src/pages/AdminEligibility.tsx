import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = (import.meta as any).env.VITE_API_BASE || "http://localhost:8000";

/**
 * Staff tool to run an on-demand payer eligibility check.
 * - Calls backend GET /v1/billing/eligibility/:patientId[?appointment_id=...]
 * - Shows status badges (Eligible / Not eligible, plan, copay)
 * - If mismatch is detected (plan mismatch or not eligible) → lets staff create a follow-up task
 * - On task creation, navigates to /admin/tasks
 */
export default function AdminEligibility() {
  const nav = useNavigate();

  // Inputs: require patient, optional appointment for tighter context
  const [patientId, setPatientId] = useState<string>("");
  const [appointmentId, setAppointmentId] = useState<string>("");

  // Results + UI state
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  async function runCheck() {
    setErr("");
    setResult(null);
    setLoading(true);
    try {
      const qs = appointmentId ? `?appointment_id=${Number(appointmentId)}` : "";
      const res = await fetch(
        `${API_BASE}/v1/billing/eligibility/${Number(patientId)}${qs}`,
        { headers: { "X-Purpose-Of-Use": "OPERATIONS" } }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || res.statusText);
      setResult(data.result || data);
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  // If a mismatch is returned, staff can open a follow-up task
  async function createTask() {
    if (!result) return;
    setCreating(true);
    setErr("");
    try {
      const body = {
        type: "eligibility_followup",
        status: "open",
        payload_json: {
          patient_id: Number(patientId),
          appointment_id: result.appointment_id || (appointmentId ? Number(appointmentId) : null),
          plan_found: result.plan || null,
          plan_recorded: result.recorded_plan || null,
          eligible: !!result.eligible,
          copay_cents: result.copay_cents ?? null,
          raw: result.raw || null,
          note: "Eligibility mismatch detected by front-desk",
        },
      };
      const r = await fetch(`${API_BASE}/v1/admin/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Purpose-Of-Use": "OPERATIONS",
        },
        body: JSON.stringify(body),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d?.detail || "Failed to create task");
      nav("/admin/tasks"); // success ⇒ go review tasks queue
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setCreating(false);
    }
  }

  function Badge({ ok, label }: { ok: boolean; label: string }) {
    // Simple status badge; green if ok, red otherwise
    return (
      <span
        className={`inline-block text-xs px-2 py-0.5 rounded ${
          ok ? "bg-green-600 text-white" : "bg-red-600 text-white"
        }`}
      >
        {label}
      </span>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Eligibility (Front-desk)</h1>

      {/* Inputs: must have patient id; appointment id optional */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex flex-col">
          <label className="text-xs text-gray-600">Patient ID</label>
          <input
            className="border rounded px-2 py-1"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            placeholder="e.g. 101"
          />
        </div>

        <div className="flex flex-col">
          <label className="text-xs text-gray-600">Appointment ID (optional)</label>
          <input
            className="border rounded px-2 py-1"
            value={appointmentId}
            onChange={(e) => setAppointmentId(e.target.value)}
            placeholder="e.g. 555"
          />
        </div>

        <button
          className="px-3 py-2 rounded bg-gray-800 text-white disabled:opacity-60"
          onClick={runCheck}
          disabled={!patientId || loading}
        >
          {loading ? "Checking..." : "Run payer check"}
        </button>
      </div>

      {err && <div className="text-red-600 text-sm">{err}</div>}

      {/* Status & details */}
      {result && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge ok={!!result.eligible} label={result.eligible ? "Eligible" : "Not eligible"} />
            {typeof result.plan === "string" && (
              <span className="text-xs border rounded px-2 py-0.5 bg-gray-50">Plan: {result.plan}</span>
            )}
            {typeof result.copay_cents === "number" && (
              <span className="text-xs border rounded px-2 py-0.5 bg-gray-50">
                Copay: ${(result.copay_cents / 100).toFixed(2)}
              </span>
            )}
            {result.recorded_plan && (
              <span className="text-xs border rounded px-2 py-0.5 bg-gray-50">
                Recorded: {result.recorded_plan}
              </span>
            )}
            {/* If mismatch, highlight it */}
            {result.mismatch && (
              <span className="text-xs px-2 py-0.5 rounded bg-yellow-500 text-black">Mismatch</span>
            )}
          </div>

          {/* Raw JSON for visibility (keeps “Run again” enabled regardless) */}
          <pre className="text-xs p-3 bg-gray-50 rounded border overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>

          {/* If mismatch → let staff create a task and jump to /admin/tasks */}
          {result.mismatch && (
            <div className="flex gap-2">
              <button
                className="px-3 py-2 rounded bg-blue-600 text-white disabled:opacity-60"
                onClick={createTask}
                disabled={creating}
              >
                {creating ? "Creating task…" : "Create follow-up task"}
              </button>
              <button
                className="px-3 py-2 rounded border"
                onClick={runCheck}
                disabled={loading}
                title="Re-run the check"
              >
                Run again
              </button>
            </div>
          )}
        </div>
      )}

      {/* Helpful links remain available */}
      <div className="text-sm mt-2">
        <a className="text-blue-600 underline" href="/billing/cases">Open Billing Cases</a>
        <span className="mx-2">•</span>
        <a className="text-blue-600 underline" href="/admin/tasks">Admin Tasks</a>
      </div>
    </div>
  );
}
