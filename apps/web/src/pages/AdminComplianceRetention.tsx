import { useState } from "react";
import { compliancePost, downloadCsv } from "../lib/api";

type RetRow = { doc_id:number; kind:string; created_at?:string; age_days:number; flagged:boolean };

export default function AdminComplianceRetention() {
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [rows, setRows] = useState<RetRow[]>([]);

  // Calls POST /v1/compliance/retention which computes counters server-side.
  // On success, we show a Download CSV button built from the returned rows.
  async function runRetention() {
    setErr(""); setMsg("");
    try {
      const r = await compliancePost<{ok:boolean; generated_at:string; rows:RetRow[]}>("/v1/compliance/retention", {});
      setRows(r.rows || []);
      setMsg(`Retention scan completed at ${r.generated_at}.`);
    } catch (e:any) {
      setErr(e.message || "Failed to run retention");
    }
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Compliance — Retention & Anomalies</h1>
      <div className="text-xs text-gray-500">
        <a className="text-blue-600 underline" href="/admin/compliance/audit">Audit</a> •
        <a className="text-blue-600 underline" href="/admin/compliance/pia">PIA/DSR</a> •
        <a className="text-blue-600 underline" href="/admin/compliance/retention">Retention</a>
      </div>

      {err && <div className="text-red-600 text-sm">{err}</div>}
      {msg && <div className="text-green-700 text-sm">{msg}</div>}

      <div className="flex flex-wrap gap-2">
        <button className="px-3 py-2 rounded bg-gray-800 text-white" onClick={runRetention}>
          Run Retention Scan
        </button>
        {rows.length > 0 && (
          <button
            className="px-3 py-2 rounded bg-gray-100"
            onClick={() => downloadCsv("retention_report.csv", rows)}
          >
            Download CSV
          </button>
        )}
      </div>

      {rows.length > 0 && (
        <div className="rounded border bg-white overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b bg-gray-50">
                <th className="p-2">Doc #</th>
                <th className="p-2">Kind</th>
                <th className="p-2">Created</th>
                <th className="p-2">Age (days)</th>
                <th className="p-2">Flagged</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r=>(
                <tr key={r.doc_id} className="border-t">
                  <td className="p-2">{r.doc_id}</td>
                  <td className="p-2">{r.kind}</td>
                  <td className="p-2">{(r.created_at||"").replace("T"," ").replace("Z","")}</td>
                  <td className="p-2">{r.age_days}</td>
                  <td className="p-2">{r.flagged ? "YES" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
