// apps/web/src/pages/Escalations.tsx
import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";

import { api } from "../lib/fetcher";            // keep for POST /v1/tasks/:id/complete
import { complianceGet } from "../lib/api";      // use this instead of apiGet for GET w/ PoU

type Patient = {
  id?: number;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
};

type Esc = {
  id: number;
  status: "open" | "in_progress" | "done" | string;
  assignee?: string | null;
  created_at?: string;
  reason?: string | null;          // e.g., "high_phq9_score"
  score?: number | null;           // e.g., PHQ-9 composite
  encounter_id?: string | null;    // e.g., "enc-123"
  survey_id?: number | null;
  patient?: Patient | null;
};

export default function OpsEscalations() {
  const [items, setItems] = useState<Esc[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);

  const load = useCallback(async () => {
    setErr("");
    setLoading(true);
    try {
      // GET /v1/ops/escalations -> { items: Esc[] }
      // Uses complianceGet from api.ts which injects PoU=OPERATIONS for GET.
      const data = await complianceGet<{ items: Esc[] }>("/v1/ops/escalations");
      setItems(Array.isArray(data?.items) ? data.items : []);
    } catch (e: any) {
      setErr(e.message || "Failed to load escalations.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function displayPatient(p?: Patient | null) {
    if (!p) return "—";
    const name = [p.first_name, p.last_name].filter(Boolean).join(" ").trim();
    return name || p.email || p.phone || (p.id ? `#${p.id}` : "—");
  }

  function badgeClass(reason?: string | null, score?: number | null) {
    // Simple severity coloring: high PHQ-9 >= 20 => red; >=15 => amber; else gray.
    if ((reason || "").includes("phq9") || (reason || "").includes("phq")) {
      if ((score ?? 0) >= 20) return "bg-red-100 text-red-700 border-red-300";
      if ((score ?? 0) >= 15) return "bg-amber-100 text-amber-700 border-amber-300";
    }
    return "bg-gray-100 text-gray-700 border-gray-300";
  }

  async function markDone(id: number) {
    setBusy(id);
    setErr("");
    try {
      // POST /v1/tasks/:id/complete (fetcher adds PoU when provided)
      await api(`/v1/tasks/${id}/complete`, { method: "POST", pou: "OPERATIONS" });
      // Optimistic update: keep row visible (per ops UX), just flip status
      setItems((prev) => prev.map((t) => (t.id === id ? { ...t, status: "done" } : t)));
    } catch (e: any) {
      setErr(e.message || "Failed to complete task.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Ops — Escalations</h1>
        <div className="flex gap-2">
          <button onClick={() => void load()} className="px-3 py-1 border rounded">
            Refresh
          </button>
          <Link to="/portal/tasks" className="px-3 py-1 border rounded">
            Patient Tasks
          </Link>
        </div>
      </div>

      {err && <div className="text-red-600 text-sm mb-3">{err}</div>}
      {loading ? (
        <div>Loading…</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full border bg-white">
            <thead className="bg-gray-50">
              <tr>
                <th className="p-2 border text-left">Patient</th>
                <th className="p-2 border text-left">Reason / Score</th>
                <th className="p-2 border text-left">Encounter</th>
                <th className="p-2 border text-left">Assignee</th>
                <th className="p-2 border text-left">Status</th>
                <th className="p-2 border text-left">Created</th>
                <th className="p-2 border text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((x) => (
                <tr key={x.id} className="border-t">
                  {/* render specific fields, not whole objects */}
                  <td className="p-2 border">{displayPatient(x.patient)}</td>
                  <td className="p-2 border">
                    <span className={`px-2 py-0.5 border rounded text-xs ${badgeClass(x.reason, x.score)}`}>
                      {x.reason || "—"} {typeof x.score === "number" ? `• ${x.score}` : ""}
                    </span>
                  </td>
                  <td className="p-2 border">{x.encounter_id || "—"}</td>
                  <td className="p-2 border">{x.assignee || "—"}</td>
                  <td className="p-2 border uppercase text-xs">{x.status || "—"}</td>
                  <td className="p-2 border">
                    {x.created_at ? new Date(x.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="p-2 border">
                    <div className="flex gap-2">
                      {x.encounter_id ? (
                        <Link className="px-2 py-1 border rounded" to={`/portal/summary/${x.encounter_id}`}>
                          Open
                        </Link>
                      ) : (
                        <Link className="px-2 py-1 border rounded" to="/portal/tasks">
                          Open
                        </Link>
                      )}
                      <button
                        className="px-2 py-1 border rounded"
                        disabled={busy === x.id || x.status === "done"}
                        onClick={() => void markDone(x.id)}
                        title="Mark as resolved (keeps row visible until refresh)"
                      >
                        {busy === x.id ? "Saving…" : x.status === "done" ? "Done" : "Mark done"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td className="p-4 text-gray-500" colSpan={7}>
                    None.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
