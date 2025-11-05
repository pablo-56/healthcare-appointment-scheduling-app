import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api } from "../lib/fetcher";

/**
 * Clinician pre-chart view for a single appointment.
 * - Loads the latest "Prechart" document for this appointment.
 * - If not ready (404), shows "generating…" with a soft refresh button.
 * - Button → Open Scribe (/provider/scribe/:appointmentId).
 */
export default function PrechartPage() {
  const { appointmentId } = useParams();
  const aid = Number(appointmentId || 0);
  const [doc, setDoc] = useState<any>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  async function load() {
    setErr("");
    setLoading(true);
    try {
      // Clinician workflow: PoU TREATMENT
      const data = await api(`/v1/prechart/${aid}`, { method: "GET", pou: "TREATMENT" });
      setDoc(data);
    } catch (e: any) {
      // 404 means "not ready yet"
      setErr(e?.message || "Not ready");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { if (aid) load(); }, [aid]);

  if (!aid) return <div className="p-6 text-red-600">Missing appointment id.</div>;

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Pre-chart (Appt #{aid})</h1>

      {loading && <div>Loading…</div>}

      {!loading && !doc && (
        <div className="space-y-2">
          <div className="text-gray-500">Prechart generating…</div>
          <button onClick={load} className="border px-3 py-1">Refresh</button>
          <div><Link className="underline" to="/">Home</Link></div>
        </div>
      )}

      {doc && (
        <div className="space-y-3">
          {/* Many pre-charts render a data: URL or S3 URL. We show both link + meta. */}
          <div className="text-sm">
            <b>Created:</b> {doc.created_at}
          </div>
          {doc.url && (
            <div>
              <a className="underline" href={doc.url} target="_blank" rel="noreferrer">
                Open pre-chart document
              </a>
            </div>
          )}
          {doc.meta && (
            <pre className="bg-black/10 p-3 rounded text-xs overflow-auto">
              {JSON.stringify(doc.meta, null, 2)}
            </pre>
          )}

          {/* Success → open Scribe */}
          <div className="flex gap-2">
            <button
              onClick={() => nav(`/provider/scribe/${aid}`)}
              className="border px-3 py-1"
            >
              Open Scribe
            </button>
            <Link to="/" className="underline">Home</Link>
          </div>
        </div>
      )}
    </div>
  );
}
