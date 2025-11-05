import { useEffect, useState } from "react";
import { api } from "../lib/fetcher";
import { downloadCsv } from "../lib/api";

// NOTE: fetcher.ts in your repo accepts { pou: "OPERATIONS" } and adds header.
// We pass PoU explicitly to be safe.

type Ops = { available?: boolean; no_show_rate?: number; tta_hours_avg?: number | null };
type Rcm = { available?: boolean; first_pass_acceptance?: number | null; dso?: number | null };

export default function Analytics() {
  const [ops, setOps] = useState<Ops | null>(null);
  const [rcm, setRcm] = useState<Rcm | null>(null);
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    try {
      const [o, r] = await Promise.all([
        api("/v1/analytics/ops", { method: "GET", pou: "OPERATIONS" }),
        api("/v1/analytics/rcm", { method: "GET", pou: "OPERATIONS" }),
      ]);
      setOps(o); setRcm(r);
    } catch (e: any) {
      const msg = String(e?.message || "Failed to load");
      setErr(/429/.test(msg) ? "Rate limited. Try again in a minute." : msg); // <- rate-limit UX
    }
  }

  useEffect(() => { load(); }, []);

  const rows = (ops && rcm) ? [{
    no_show_rate: ops.no_show_rate ?? null,
    tta_hours_avg: ops.tta_hours_avg ?? null,
    first_pass_acceptance: rcm.first_pass_acceptance ?? null,
    dso_days: rcm.dso ?? null,
  }] : [];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Analytics</h1>
      {err && <div className="text-red-600 text-sm">{err}</div>}

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Ops — No-show rate">
          <Metric value={pct(ops?.no_show_rate)} note="lower is better" />
        </Card>
        <Card title="Ops — Avg time to appointment (hours)">
          <Metric value={num(ops?.tta_hours_avg)} />
        </Card>
        <Card title="RCM — First-pass acceptance">
          <Metric value={pct(rcm?.first_pass_acceptance)} note="higher is better" />
        </Card>
        <Card title="RCM — DSO (days)">
          <Metric value={num(rcm?.dso)} />
        </Card>
      </div>

      <div className="flex gap-2">
        <button
          className="px-3 py-2 rounded bg-gray-800 text-white"
          onClick={() => downloadCsv("analytics.csv", rows)}
          disabled={!rows.length}
        >
          Export CSV
        </button>
        {/* Static shortcut to your Grafana board */}
        <a className="px-3 py-2 rounded bg-gray-100" href="http://localhost:3000/" target="_blank" rel="noreferrer">
          Open Grafana →
        </a>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: any }) {
  return (
    <div className="rounded-xl border border-gray-200 p-4 shadow-sm bg-white">
      <div className="text-sm text-gray-500">{title}</div>
      <div className="mt-2">{children}</div>
    </div>
  );
}
function Metric({ value, note }: { value?: string; note?: string }) {
  return (
    <div>
      <div className="text-3xl font-semibold">{value ?? "—"}</div>
      {note && <div className="text-xs text-gray-500">{note}</div>}
    </div>
  );
}
const pct = (v?: number | null) => (v ?? null) === null ? undefined : `${(v! * 100).toFixed(1)}%`;
const num = (v?: number | null) => (v ?? null) === null ? undefined : String(Number(v).toFixed(1));
