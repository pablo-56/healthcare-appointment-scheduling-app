import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

type Patient = {
  id?: number | string;
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  [k: string]: any;
};

type QueueItem = {
  id?: number | string;                 // some APIs use this as the appointment id
  appointment_id?: number | string;     // explicit id if present
  start_at?: string;                    // ISO
  appt_time?: string;                   // alt
  datetime?: string;                    // alt
  when?: string;                        // alt
  reason?: string;
  status?: string;
  wait_minutes?: number | null;
  patient?: Patient | null;             // NESTED OBJECT – render fields only
  [k: string]: any;
};

export default function Queue() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const nav = useNavigate();

  // ---- load queue (OPS PoU) -------------------------------------------------
  useEffect(() => {
    (async () => {
      setErr("");
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/v1/ops/queue`, {
          headers: { "X-Purpose-Of-Use": "OPERATIONS" },
        });
        const data = await res.json().catch(() => ({}));
        const arr: QueueItem[] = Array.isArray(data?.items)
          ? data.items
          : Array.isArray(data)
          ? data
          : [];
        setItems(arr);
      } catch (e: any) {
        setErr(e?.message || "Failed to load queue.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Render *fields*, not raw objects (requirement)
  function displayPatient(p?: Patient | null) {
    if (!p) return "—";
    const name = [p.first_name, p.last_name].filter(Boolean).join(" ");
    return name || p.email || p.phone || `#${p.id ?? ""}`;
  }

  function fmtTime(s?: string) {
    if (!s) return "—";
    const d = new Date(s);
    return isNaN(+d) ? s : d.toLocaleString();
  }

  function getApptId(q: QueueItem) {
    return q.appointment_id ?? q.id;
  }

  // ---- PATCH status (OPS PoU) -----------------------------------------------
  async function patchStatus(apptId: number | string, status: string) {
    const res = await fetch(`${API_BASE}/v1/appointments/${apptId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Purpose-Of-Use": "OPERATIONS",
      },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) {
      const t = await res.text().catch(() => "");
      throw new Error(t || `PATCH ${res.status}`);
    }
    return res.json().catch(() => ({}));
  }

  async function markArrived(q: QueueItem) {
    const apptId = getApptId(q);
    if (!apptId) return;
    try {
      // Optimistic: update UI immediately; roll back on failure
      const prev = q.status;
      setItems((list) => list.map((it) => (getApptId(it) === apptId ? { ...it, status: "ARRIVED" } : it)));
      await patchStatus(apptId, "ARRIVED");
    } catch (e) {
      setErr((e as any)?.message || "Failed to update status");
      setItems((list) => list.map((it) => (getApptId(it) === apptId ? { ...it, status: q.status } : it)));
    }
  }

  // Mark ARRIVED → open kiosk check-in with the appointment id prefilled
  async function arriveAndOpen(q: QueueItem) {
    const apptId = getApptId(q);
    if (!apptId) return;
    try {
      await markArrived(q);
      nav(`/check-in?aid=${apptId}`);
    } catch {
      /* no-op: error already surfaced */
    }
  }

  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold mb-4">Ops Queue</h1>

      {err && <div className="text-red-500 mb-3">{err}</div>}
      {loading ? (
        <div>Loading…</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full border">
            <thead className="bg-gray-50">
              <tr>
                <th className="p-2 border">Patient</th>
                <th className="p-2 border">Appt time</th>
                <th className="p-2 border">Reason</th>
                <th className="p-2 border">Status</th>
                <th className="p-2 border">Wait</th>
                <th className="p-2 border">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((q) => {
                const apptId = getApptId(q);
                const apptTime = q.start_at ?? q.appt_time ?? q.datetime ?? q.when;
                return (
                  <tr key={String(apptId)}>
                    <td className="p-2 border">{displayPatient(q.patient)}</td>
                    <td className="p-2 border">{fmtTime(apptTime)}</td>
                    <td className="p-2 border">{q.reason || "—"}</td>
                    <td className="p-2 border">{q.status || "—"}</td>
                    <td className="p-2 border">{q.wait_minutes ?? "—"}</td>
                    <td className="p-2 border">
                      <div className="flex gap-2">
                        <button className="px-2 py-1 border rounded" onClick={() => markArrived(q)}>
                          Arrived
                        </button>
                        <button className="px-2 py-1 border rounded" onClick={() => arriveAndOpen(q)}>
                          Check-in
                        </button>
                        {/* Optional: quick rooming / no-show helpers */}
                        <button className="px-2 py-1 border rounded" onClick={() => patchStatus(apptId!, "IN_ROOM").then(() =>
                          setItems((list) => list.map((it) => (getApptId(it) === apptId ? { ...it, status: "IN_ROOM" } : it)))
                        )}>
                          Room
                        </button>
                        <button className="px-2 py-1 border rounded" onClick={() => patchStatus(apptId!, "NO_SHOW").then(() =>
                          setItems((list) => list.map((it) => (getApptId(it) === apptId ? { ...it, status: "NO_SHOW" } : it)))
                        )}>
                          No-show
                        </button>
                        {/* Clinician shortcut – summary if encounter already exists */}
                        <Link className="px-2 py-1 border rounded" to={`/portal/summary/${q.encounterId ?? apptId}`}>
                          Summary
                        </Link>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {items.length === 0 && (
                <tr>
                  <td className="p-4 text-gray-500" colSpan={6}>
                    No patients in queue.
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
