// apps/web/src/pages/Scribe.tsx
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_BASE;

export default function ScribePage() {
  const { appointmentId } = useParams();
  const apptId = useMemo(() => Number(appointmentId), [appointmentId]);

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>("");

  async function startSession() {
    setErr("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/v1/scribe/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Purpose-Of-Use": "TREATMENT", // REQUIRED by backend
        },
        body: JSON.stringify({ appointment_id: apptId }),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}: ${t}`);
      }
      const data = await res.json();
      setSessionId(data.session_id);
      setDraft(data.draft || "");
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  async function approve() {
    if (!sessionId) return;
    setErr("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/v1/scribe/sessions/${sessionId}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Purpose-Of-Use": "TREATMENT",
        },
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`HTTP ${res.status}: ${t}`);
      }
      // Optionally: toast or navigate
      alert("Approved & sent to EHR (mock). Coding review task created.");
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // no-op; page waits for user to click "Start scribe session"
  }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-3xl font-semibold">Ambient Scribe (Appointment #{apptId})</h1>

      <div>
        <button
          className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
          onClick={startSession}
          disabled={loading}
        >
          Start scribe session
        </button>
      </div>

      {err ? <p className="text-red-400">Error: {err}</p> : null}
      {loading ? <p>Loading…</p> : null}

      {sessionId ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-300">Session ID: {sessionId}</p>
          <textarea
            className="w-full h-64 p-3 rounded bg-gray-900 border border-gray-700"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="flex gap-3">
            {/* In a real app you'd persist edits; here we just approve the current draft. */}
            <button
              className="px-4 py-2 rounded bg-emerald-600 text-white disabled:opacity-50"
              onClick={approve}
              disabled={loading}
            >
              Approve & Post to EHR (mock)
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
