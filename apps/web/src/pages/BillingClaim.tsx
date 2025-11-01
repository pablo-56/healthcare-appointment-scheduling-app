// apps/web/src/pages/BillingClaim.tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

/**
 * Claim detail page with a "Submit" button. Uses PAYMENT PoU.
 */
export default function BillingClaim() {
  const { id } = useParams();
  const [rec, setRec] = useState<any>(null);
  const [err, setErr] = useState<string>("");

  async function load() {
    setErr("");
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE}/v1/claims/${id}`, {
        headers: { "X-Purpose-Of-Use": "PAYMENT" },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      setRec(await res.json());
    } catch (e: any) {
      setErr(String(e));
    }
  }

  useEffect(() => { load(); }, [id]);

  async function submit() {
    setErr("");
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE}/v1/claims/${id}/submit`, {
        method: "POST",
        headers: { "X-Purpose-Of-Use": "PAYMENT" },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      await load();
    } catch (e: any) {
      setErr(String(e));
    }
  }

  if (!rec) return <div className="p-6">Loading… {err && <span className="text-red-400 ml-2">{err}</span>}</div>;

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Claim #{rec.id}</h1>
      {err && <div className="text-red-400">Error: {err}</div>}
      <div className="space-y-1">
        <div><b>Status:</b> {rec.status}</div>
        <div><b>Encounter:</b> {rec.encounter_id}</div>
        <div><b>Payer Ref:</b> {rec.payer_ref || "—"}</div>
        <div><b>Total:</b> ${((rec.total_cents || 0) / 100).toFixed(2)}</div>
        <div className="mt-2">
          <button onClick={submit} className="px-3 py-2 rounded bg-blue-600 hover:bg-blue-700">
            Submit to clearinghouse
          </button>
        </div>
      </div>
      <pre className="text-xs bg-black/30 p-3 rounded overflow-auto">
        {JSON.stringify(rec.payload_json, null, 2)}
      </pre>
    </div>
  );
}
