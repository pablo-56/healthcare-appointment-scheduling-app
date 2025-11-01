import { useEffect, useState } from "react";

type Ops = { available: boolean; no_show_rate: number|null; tta_hours_avg: number|null };
type Rcm = { available: boolean; first_pass_acceptance: number|null; dso: number|null; dso_available: boolean };

const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function Analytics() {
  const [ops, setOps] = useState<Ops | null>(null);
  const [rcm, setRcm] = useState<Rcm | null>(null);
  const [err, setErr] = useState("");

  async function fetchOps() {
    setErr("");
    try {
      const res = await fetch(`${API}/v1/analytics/ops`, {
        headers: { "X-Purpose-Of-Use": "OPERATIONS" },
      });
      setOps(await res.json());
    } catch (e:any) { setErr(e.message || "failed"); }
  }

  async function fetchRcm() {
    setErr("");
    try {
      const res = await fetch(`${API}/v1/analytics/rcm`, {
        headers: { "X-Purpose-Of-Use": "OPERATIONS" },
      });
      setRcm(await res.json());
    } catch (e:any) { setErr(e.message || "failed"); }
  }

  useEffect(() => { fetchOps(); fetchRcm(); }, []);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Analytics</h1>
      {err && <div className="text-red-500">{err}</div>}

      <section className="p-4 rounded-xl shadow bg-neutral-900 text-neutral-100">
        <h2 className="text-xl mb-4">Ops</h2>
        {!ops ? <div>Loading...</div> : (
          <div className="space-y-1">
            <div>Available: {String(ops.available)}</div>
            <div>No-show rate: {ops.no_show_rate == null ? "n/a" : ops.no_show_rate.toFixed(3)}</div>
            <div>TTA (avg hours): {ops.tta_hours_avg == null ? "n/a" : ops.tta_hours_avg.toFixed(2)}</div>
            <a className="underline" href={`${API}/v1/analytics/ops?csv=1`} target="_blank">Download CSV</a>
          </div>
        )}
      </section>

      <section className="p-4 rounded-xl shadow bg-neutral-900 text-neutral-100">
        <h2 className="text-xl mb-4">RCM</h2>
        {!rcm ? <div>Loading...</div> : (
          <div className="space-y-1">
            <div>Available: {String(rcm.available)}</div>
            <div>First-pass acceptance: {rcm.first_pass_acceptance == null ? "n/a" : rcm.first_pass_acceptance.toFixed(3)}</div>
            <div>DSO: {rcm.dso_available ? (rcm.dso == null ? "n/a" : rcm.dso.toFixed(2) + " days") : "not available"}</div>
            <a className="underline" href={`${API}/v1/analytics/rcm?csv=1`} target="_blank">Download CSV</a>
          </div>
        )}
      </section>
    </div>
  );
}
