// apps/web/src/pages/Prechart.tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

const API = (import.meta as any).env.VITE_API_BASE || "http://localhost:8000";

type Prechart = {
  document_id: number;
  url: string;
  meta?: any;
  created_at: string;
};

export default function PrechartPage() {
  const { appointmentId } = useParams<{ appointmentId: string }>();
  const [data, setData] = useState<Prechart | null>(null);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!appointmentId) return;
      setErr("");
      setData(null);
      try {
        const r = await fetch(`${API}/v1/prechart/${appointmentId}`, {
          headers: {
            "X-Purpose-Of-Use": "OPERATIONS",
            Accept: "application/json",
          },
        });

        // Read as text first so we can show helpful error if backend returns HTML
        const txt = await r.text();
        if (!r.ok) {
          throw new Error(`HTTP ${r.status}: ${txt.slice(0, 160)}`);
        }

        let j: any;
        try {
          j = JSON.parse(txt);
        } catch {
          throw new Error(`Backend returned non-JSON: ${txt.slice(0, 160)}`);
        }

        if (!cancelled) setData(j as Prechart);
      } catch (e: any) {
        if (!cancelled) setErr(e?.message ?? String(e));
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [appointmentId]);

  return (
    <div style={{ padding: 16 }}>
      <h1>Prechart</h1>
      {err && <div style={{ color: "crimson", marginBottom: 8 }}>Error: {err}</div>}
      {!data ? (
        <div>Loading…</div>
      ) : (
        <>
          <div style={{ marginBottom: 12 }}>
            <div><b>Document ID:</b> {data.document_id}</div>
            <div><b>Created:</b> {new Date(data.created_at).toLocaleString()}</div>
          </div>
          <iframe
            title="Prechart Document"
            src={data.url}
            style={{ width: "100%", height: "80vh", border: "1px solid #ddd", borderRadius: 8 }}
          />
        </>
      )}
    </div>
  );
}
