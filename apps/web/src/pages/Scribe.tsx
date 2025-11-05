import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "../lib/fetcher";

/**
 * In-room Scribe for a specific appointment.
 * - Start -> POST /v1/scribe/sessions { appointment_id }
 * - Always keep a manual draft text area enabled (even if audio/LLM fails).
 * - Approve -> POST /v1/scribe/sessions/:sessionId/approve
 * - On approve: show buttons to Summary and Billing cases.
 */
export default function ScribePage() {
  const { appointmentId } = useParams();
  const aid = Number(appointmentId || 0);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [draft, setDraft] = useState<string>("");              // manual-friendly
  const [err, setErr] = useState("");
  const [approved, setApproved] = useState(false);
  const nav = useNavigate();

  async function start() {
    setErr("");
    try {
      const r = await api("/v1/scribe/sessions", {
        method: "POST",
        body: JSON.stringify({ appointment_id: aid }),
        pou: "TREATMENT",
      });
      setSessionId(r.session_id);
      // Use server draft if present, otherwise keep any local edits
      setDraft((d) => (d?.trim()?.length ? d : (r.draft || "Draft ready")));
    } catch (e:any) {
      // Audio/stream/model failures should NOT block manual note: keep the text area enabled
      setErr(e.message || "Could not start scribe. Manual note entry enabled.");
      if (!draft) setDraft("Manual note. Audio/stream temporarily unavailable.");
    }
  }

  async function approve() {
    setErr("");
    try {
      if (!sessionId) throw new Error("Start a scribe session first");
      // Include the latest draft in approve call (backend can store it or ignore)
      await api(`/v1/scribe/sessions/${sessionId}/approve`, {
        method: "POST",
        body: JSON.stringify({ draft }),
        pou: "TREATMENT",
      });
      setApproved(true);
    } catch (e:any) {
      setErr(e.message || "Could not approve note.");
    }
  }

  if (!aid) return <div className="p-6 text-red-600">Missing appointment id.</div>;

  return (
    <div className="p-6 space-y-3">
      <h1 className="text-2xl font-semibold">In-room Scribe (Appt #{aid})</h1>

      <div className="flex gap-2">
        <button className="px-3 py-1 border" onClick={start} disabled={!!sessionId}>
          {sessionId ? `Session #${sessionId}` : "Start"}
        </button>
        <Link to={`/provider/prechart/${aid}`} className="border px-3 py-1">Pre-chart</Link>
      </div>

      {err && <div className="text-red-600 text-sm">{err}</div>}

      {/* Manual draft is always available */}
      <textarea
        className="w-full border rounded p-2 h-56"
        placeholder="SOAP note draft…"
        value={draft}
        onChange={(e)=>setDraft(e.target.value)}
      />

      <div className="flex gap-2">
        <button className="px-3 py-1 border" onClick={approve} disabled={!sessionId || approved}>
          {approved ? "Approved" : "Approve"}
        </button>
        <Link className="px-3 py-1 border" to="/">Home</Link>
      </div>

      {/* After approve → links to Summary and Billing cases */}
      {approved && (
        <div className="space-x-2 mt-3">
          <button className="border px-3 py-1" onClick={() => nav(`/portal/summary/enc-${aid}`)}>
            Open Summary
          </button>
          <button className="border px-3 py-1" onClick={() => nav("/billing/cases")}>
            Billing cases
          </button>
        </div>
      )}
    </div>
  );
}
