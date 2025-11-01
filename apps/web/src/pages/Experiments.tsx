import { useState } from "react";

const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function Experiments() {
  const [name, setName] = useState("reminder_ab");
  const [body, setBody] = useState<any>({
    status: "open",
    variants: {
      A: { subject: "Your appointment is tomorrow", channel: "email", timing: "24h" },
      B: { subject: "Reminder: appointment coming up", channel: "sms", timing: "48h" },
    }
  });
  const [resp, setResp] = useState<any>(null);
  const [err, setErr] = useState("");

  async function save() {
    setErr(""); setResp(null);
    try {
      const res = await fetch(`${API}/v1/experiments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Purpose-Of-Use": "OPERATIONS",
        },
        body: JSON.stringify({ name, ...body }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResp(await res.json());
    } catch (e:any) { setErr(e.message || "failed"); }
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Experiments</h1>
      <div className="space-y-2">
        <label className="block">Name</label>
        <input className="bg-neutral-900 text-neutral-100 rounded p-2 w-full"
               value={name} onChange={e=>setName(e.target.value)} />
      </div>

      <div className="space-y-2">
        <label className="block">JSON (status, variants)</label>
        <textarea className="bg-neutral-900 text-neutral-100 rounded p-2 w-full h-48"
          value={JSON.stringify(body, null, 2)}
          onChange={e=>{
            try { setBody(JSON.parse(e.target.value)); setErr(""); }
            catch { setErr("Invalid JSON"); }
          }}
        />
      </div>

      <button onClick={save}
        className="px-4 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700">
        Save / Upsert
      </button>

      {err && <div className="text-red-500">{err}</div>}
      {resp && <pre className="bg-neutral-900 text-neutral-100 p-3 rounded">{JSON.stringify(resp, null, 2)}</pre>}
    </div>
  );
}

