import { useEffect, useState } from "react";
import { complianceGet, downloadCsv } from "../lib/api";

type Row = {
  id: number;
  actor?: string;
  action?: string;
  target?: string;
  details?: any;
  created_at?: string;
  patient_id?: number | null;
};

export default function AdminComplianceAudit() {
  const [actor, setActor] = useState("");
  const [patientId, setPatientId] = useState<number | "">("");
  const [items, setItems] = useState<Row[]>([]);
  const [err, setErr] = useState("");

  // Loads with PoU=OPERATIONS header (enforced by complianceGet()).
  // If backend still returns 400/401, show an admin hint to check headers.
  async function load() {
    setErr("");
    const qs = new URLSearchParams();
    if (actor) qs.set("actor", actor);
    if (patientId !== "") qs.set("patient_id", String(patientId));
    try {
      const data = await complianceGet<{items: Row[]; count: number}>(`/v1/compliance/audit?${qs}`);
      setItems(data.items || []);
    } catch (e: any) {
      const msg = String(e?.message || "Failed to load");
      setErr(/401|400/i.test(msg)
        ? `${msg}. Hint: ensure X-Purpose-Of-Use: OPERATIONS is sent.`
        : msg);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Compliance — Audit</h1>
      <div className="text-xs text-gray-500">
        <a className="text-blue-600 underline" href="/admin/compliance/audit">Audit</a> •
        <a className="text-blue-600 underline" href="/admin/compliance/pia">PIA/DSR</a> •
        <a className="text-blue-600 underline" href="/admin/compliance/retention">Retention</a>
      </div>

      {err && <div className="text-red-600 text-sm">{err}</div>}

      <div className="flex flex-wrap gap-2 items-end">
        <div className="flex flex-col">
          <label className="text-xs">Actor</label>
          <input className="border rounded px-2 py-1" value={actor} onChange={(e)=>setActor(e.target.value)} />
        </div>
        <div className="flex flex-col">
          <label className="text-xs">Patient ID</label>
          <input className="border rounded px-2 py-1"
            value={patientId}
            onChange={(e)=>setPatientId(e.target.value ? Number(e.target.value) : "")}/>
        </div>
        <button className="px-3 py-2 rounded bg-gray-800 text-white" onClick={load}>Search</button>
        <button className="px-3 py-2 rounded bg-gray-100" onClick={() => downloadCsv("audit.csv", items)}>CSV</button>
      </div>

      <div className="rounded-xl border bg-white overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b bg-gray-50">
              <th className="p-2">Time</th>
              <th className="p-2">Actor</th>
              <th className="p-2">Action</th>
              <th className="p-2">Target</th>
              <th className="p-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r)=>(
              <tr key={r.id} className="border-t">
                <td className="p-2 whitespace-nowrap">{r.created_at?.replace("T"," ").replace("Z","")}</td>
                <td className="p-2">{r.actor||"—"}</td>
                <td className="p-2">{r.action||"—"}</td>
                <td className="p-2">{r.target||"—"}</td>
                <td className="p-2 text-xs">
                  <pre className="whitespace-pre-wrap">{JSON.stringify(r.details ?? {}, null, 2)}</pre>
                </td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={5} className="p-4 text-gray-500">No audit rows.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
