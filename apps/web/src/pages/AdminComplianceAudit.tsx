import { useEffect, useState } from "react";

export default function AdminComplianceAudit() {
  const [items, setItems] = useState<any[]>([]);
  const [actor, setActor] = useState("");
  const [patientId, setPatientId] = useState<string>("");
  const [err, setErr] = useState("");

  async function load() {
    setErr("");
    try {
      const qs = new URLSearchParams();
      if (actor) qs.set("actor", actor);
      if (patientId) qs.set("patient_id", patientId);
      const res = await fetch(`/v1/compliance/audit?${qs.toString()}`, {
        headers: { "X-Purpose-Of-Use": "OPERATIONS" },
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      setItems(json.items || []);
    } catch (e: any) {
      setErr(String(e));
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Compliance &rsaquo; Audit</h1>
      <div className="flex gap-2">
        <input className="border p-2 rounded" placeholder="actor email"
               value={actor} onChange={(e)=>setActor(e.target.value)} />
        <input className="border p-2 rounded" placeholder="patient_id"
               value={patientId} onChange={(e)=>setPatientId(e.target.value)} />
        <button onClick={load} className="px-3 py-2 bg-black text-white rounded">Refresh</button>
      </div>
      {err && <div className="text-red-600">{err}</div>}
      <table className="w-full text-sm">
        <thead><tr><th className="text-left">ts</th><th>actor</th><th>action</th><th>route</th><th>patient</th><th>meta</th></tr></thead>
        <tbody>
          {items.map(r => (
            <tr key={r.id} className="border-t">
              <td>{r.ts}</td><td>{r.actor}</td><td>{r.action}</td>
              <td>{r.route}</td><td>{r.patient_id ?? "-"}</td>
              <td><pre className="whitespace-pre-wrap">{JSON.stringify(r.meta || {}, null, 2)}</pre></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
