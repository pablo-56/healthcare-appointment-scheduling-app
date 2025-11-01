// apps/web/src/pages/PortalSummary.tsx
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

export default function PortalSummaryPage() {
  const { encounterId } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [err, setErr] = useState<string>("");
  const [url, setUrl] = useState<string>("");

  useEffect(() => {
    async function load() {
      setErr("");
      setUrl("");
      try {
        const res = await fetch(
          `${import.meta.env.VITE_API_BASE}/v1/documents/discharge/${encounterId}?token=${encodeURIComponent(token)}`
        );
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
        const data = await res.json();
        setUrl(data.url);
      } catch (e: any) {
        setErr(String(e.message || e));
      }
    }
    if (encounterId && token) load();
  }, [encounterId, token]);

  return (
    <div style={{ padding: 24 }}>
      <h1>Discharge Summary</h1>
      {err && <p style={{ color: "tomato" }}>Error: {err}</p>}
      {!url && <p>Loading…</p>}
      {url && (
        <iframe
          src={url}
          style={{ width: "100%", height: "75vh", border: "1px solid #333", borderRadius: 8 }}
          title="discharge"
        />
      )}
    </div>
  );
}
