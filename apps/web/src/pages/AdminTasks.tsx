import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

type TaskItem = {
  id: number;
  type: string;
  status: string;                // open | in_progress | done | canceled
  payload_json: any;             // may contain appointment_id, claim_id, request_id, etc.
  assignee?: string | null;
  created_at?: string;
};

const API_BASE = (import.meta as any).env.VITE_API_BASE || "http://localhost:8000";
const PAGE_SIZE = 25;

/**
 * Front-desk / Ops Tasks worklist.
 * - Loads tasks via GET /v1/tasks with PoU=OPERATIONS
 * - Keyset pagination using ?before_id=...
 * - Each row has an "Open" action that routes to Intake, Consent, or BillingClaim
 * - Completing a task does NOT remove the row on failure (safe UI)
 */
export default function AdminTasks() {
  const nav = useNavigate();

  const [items, setItems] = useState<TaskItem[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  // keyset pagination
  const [beforeId, setBeforeId] = useState<number | null>(null);
  const [hasMore, setHasMore] = useState(false);

  async function load(reset = false) {
    setErr("");
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      qs.set("limit", String(PAGE_SIZE));
      if (!reset && beforeId) qs.set("before_id", String(beforeId));

      const res = await fetch(`${API_BASE}/v1/tasks?${qs.toString()}`, {
        headers: { "X-Purpose-Of-Use": "OPERATIONS" },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.detail || "Failed to load tasks");

      const arr: TaskItem[] = Array.isArray(data?.items) ? data.items : [];
      if (reset) {
        setItems(arr);
      } else {
        setItems((prev) => [...prev, ...arr]);
      }
      // if we got a full page, there might be more; remember last id as next cursor
      setHasMore(arr.length === PAGE_SIZE);
      if (arr.length) setBeforeId(arr[arr.length - 1].id);
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // initial load (reset=true)
    setBeforeId(null);
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Decide where "Open" should go for a given task
  function pathForTask(t: TaskItem): string | null {
    const p = t.payload_json || {};
    // Coverage gap / eligibility mismatch → Intake for that appointment
    if (t.type === "eligibility_followup" || p.kind === "coverage_gap") {
      const aid = p.appointment_id || p.appt_id || p.aid;
      if (aid) return `/intake/${aid}`;
    }
    // Signature issue → Consent (keep docs link visible on that page)
    if (t.type === "signature_issue" || p.kind === "signature_retry" || p.request_id) {
      const rid = p.request_id || p.sig_request_id;
      const aid = p.appointment_id || p.appt_id;
      if (rid) return `/consent/${String(rid)}${aid ? `?appt=${aid}` : ""}`;
    }
    // Coding / billing → Claim detail
    if (t.type === "coding_review" || p.claim_id) {
      const cid = p.claim_id || p.id;
      if (cid) return `/billing/claims/${cid}`;
    }
    // Fallback: if only appointment_id is present, send to intake
    if (p.appointment_id) return `/intake/${p.appointment_id}`;
    return null;
  }

  async function complete(id: number) {
    // Do not optimistically remove the row; failure must keep the row visible
    try {
      const r = await fetch(`${API_BASE}/v1/tasks/${id}/complete`, {
        method: "POST",
        headers: { "X-Purpose-Of-Use": "OPERATIONS" },
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d?.detail || "Could not complete task");
      // Soft update the status to "done"; keep the row rendered
      setItems((prev) => prev.map((t) => (t.id === id ? { ...t, status: "done" } : t)));
    } catch (e: any) {
      // Show an inline error but do NOT remove the row
      setErr(e.message || "Failed to complete task");
    }
  }

  const rows = useMemo(() => items, [items]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Operations Tasks</h1>

      <div className="flex items-center gap-2">
        <button
          className="border px-3 py-1"
          onClick={() => {
            setBeforeId(null);
            load(true); // refresh reset
          }}
          disabled={loading}
          title="Refresh"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
        <button
          className="border px-3 py-1"
          onClick={() => load(false)}
          disabled={loading || !hasMore}
          title="Older"
        >
          Load older
        </button>
      </div>

      {err && <div className="text-red-600 text-sm">{err}</div>}

      {rows.length === 0 && !loading && <div className="text-gray-500">No tasks.</div>}

      <div className="overflow-x-auto">
        <table className="min-w-full border">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-2 border">#</th>
              <th className="p-2 border">Type</th>
              <th className="p-2 border">Status</th>
              <th className="p-2 border">Created</th>
              <th className="p-2 border">Summary</th>
              <th className="p-2 border">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const to = pathForTask(t);
              const p = t.payload_json || {};
              return (
                <tr key={t.id} className={t.status === "done" ? "opacity-70" : ""}>
                  <td className="p-2 border align-top">#{t.id}</td>
                  <td className="p-2 border align-top">{t.type}</td>
                  <td className="p-2 border align-top">{t.status}</td>
                  <td className="p-2 border align-top">
                    {t.created_at ? new Date(t.created_at).toLocaleString() : "—"}
                  </td>
                  {/* Render fields, not whole object: show a compact, human summary */}
                  <td className="p-2 border text-sm align-top">
                    {[
                      p.appointment_id ? `Appt: ${p.appointment_id}` : null,
                      p.claim_id ? `Claim: ${p.claim_id}` : null,
                      p.request_id ? `SigReq: ${p.request_id}` : null,
                      typeof p.plan_found === "string" ? `Plan: ${p.plan_found}` : null,
                      typeof p.copay_cents === "number" ? `Copay: $${(p.copay_cents / 100).toFixed(2)}` : null,
                    ]
                      .filter(Boolean)
                      .join(" • ") || "—"}
                  </td>
                  <td className="p-2 border align-top">
                    <div className="flex flex-wrap gap-2">
                      {to ? (
                        <Link className="border px-3 py-1" to={to}>
                          Open
                        </Link>
                      ) : (
                        <button className="border px-3 py-1 opacity-60 cursor-not-allowed" disabled>
                          Open
                        </button>
                      )}
                      {t.status !== "done" && (
                        <button className="border px-3 py-1" onClick={() => complete(t.id)}>
                          Complete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {loading && (
              <tr>
                <td className="p-3 text-gray-500" colSpan={6}>
                  Loading…
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
