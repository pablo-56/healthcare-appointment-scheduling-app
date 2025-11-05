import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/fetcher";

/**
 * Claim detail page.
 * - GET /v1/billing/claims/:id
 * - Submit/Resubmit -> POST /v1/billing/claims/:id/submit
 * - If payer denies (later via mock 835), show Edit Codes link back to Scribe.
 */
export default function BillingClaim() {
  const { id } = useParams();
  const [claim, setClaim] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setMsg("");
    try {
      const data = await api(`/v1/billing/claims/${id}`, { method: "GET", pou: "PAYMENT" });
      setClaim(data);
    } catch (e:any) {
      setMsg(e.message || "Failed to load claim");
    }
  }
  useEffect(() => { load(); }, [id]);

  async function submit() {
    if (!id) return;
    setBusy(true);
    setMsg("");
    try {
      const res = await api(`/v1/billing/claims/${id}/submit`, { method: "POST", pou: "PAYMENT" });
      setMsg(`Submitted. Payer ref: ${res.payer_ref}`);
      await load();
    } catch (e:any) {
      setMsg(e.message || "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  const apptId = claim?.appointment_id;

  return (
    <div className="p-6 space-y-3">
      <h1 className="text-2xl font-semibold">Claim #{id}</h1>
      {msg && <div className="text-sm">{msg}</div>}

      {!claim ? (
        <div className="text-gray-500">Loading…</div>
      ) : (
        <>
          <div className="text-sm">Status: <b>{claim.status}</b></div>
          {claim.payer_ref && <div className="text-sm">Payer ref: {claim.payer_ref}</div>}
          <pre className="text-xs border rounded p-3 bg-white overflow-auto">
            {JSON.stringify(claim, null, 2)}
          </pre>

          <div className="flex gap-2">
            <button onClick={submit} disabled={busy} className="border px-3 py-1">
              {busy ? "Submitting…" : (claim.status === "NEW" ? "Submit" : "Resubmit")}
            </button>
            {/* If denied/rejected, make it easy to go edit codes (via Scribe for demo) */}
            {(claim.status === "DENIED" || claim.status === "REJECTED") && apptId && (
              <Link to={`/provider/scribe/${apptId}`} className="border px-3 py-1">Edit codes</Link>
            )}
            <Link to="/billing/cases" className="border px-3 py-1">Back</Link>
          </div>
        </>
      )}
    </div>
  );
}
