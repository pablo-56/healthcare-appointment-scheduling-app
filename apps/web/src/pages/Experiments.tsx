import { useEffect, useState } from "react";
import { api } from "../lib/fetcher";

type Variant = { name: string; subject?: string; channel?: "sms"|"email"; timing_min?: number };
type ExperimentRow = { id:number; name:string; status:string; variants:any; created_at?:string };

export default function Experiments() {
  const [name, setName] = useState("reminders_v1");
  const [variants, setVariants] = useState<Variant[]>([
    { name: "A", subject: "Reminder A", channel: "sms", timing_min: 24*60 },
    { name: "B", subject: "Reminder B", channel: "email", timing_min: 12*60 },
  ]);
  const [list, setList] = useState<ExperimentRow[]>([]);
  const [err, setErr] = useState(""); const [msg, setMsg] = useState("");

  function validate(): string | null {
    for (const v of variants) {
      if (!v.name) return "Variant name is required";
      if (!v.subject) return `Variant ${v.name}: subject is required`;
      if (v.channel !== "sms" && v.channel !== "email") return `Variant ${v.name}: channel must be sms or email`;
      const t = Number(v.timing_min ?? 0);
      if (!Number.isFinite(t) || t <= 0) return `Variant ${v.name}: timing_min must be a positive integer`;
    }
    return null;
  }

  async function save() {
    setErr(""); setMsg("");
    const validation = validate();
    if (validation) { setErr(validation); return; }

    // Convert array → dict shape expected by API
    const variantsDict = Object.fromEntries(variants.map(v => [v.name, {
      subject: v.subject, channel: v.channel, timing_min: Number(v.timing_min)
    }]));

    try {
      await api("/v1/experiments", {
        method: "POST",
        body: JSON.stringify({ name, status: "open", variants: variantsDict }),
        pou: "OPERATIONS",
      });
      setMsg("Experiment saved.");
      await load();
    } catch (e:any) {
      setErr(e.message || "Failed to save");
    }
  }

  async function load() {
    setErr("");
    try {
      const r = await api("/v1/experiments", { method: "GET", pou: "OPERATIONS" });
      setList(Array.isArray(r?.items) ? r.items : []);
    } catch (e:any) {
      setErr(e.message || "Failed to load");
    }
  }
  useEffect(() => { load(); }, []);

  function patchVariant(i:number, patch:Partial<Variant>) {
    setVariants(prev => prev.map((v,idx)=> idx===i ? {...v, ...patch} : v));
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Experiments</h1>
      {err && <div className="text-red-600 text-sm">{err}</div>}
      {msg && <div className="text-green-700 text-sm">{msg}</div>}

      <div className="rounded-xl border p-4 bg-white space-y-3">
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-600">Experiment name</label>
          <input className="border rounded px-2 py-1" value={name} onChange={(e)=>setName(e.target.value)} />
        </div>

        <div className="space-y-2">
          <div className="text-sm text-gray-600">Variants</div>
          {variants.map((v, i) => (
            <div key={i} className="grid md:grid-cols-4 gap-2">
              <input className="border rounded px-2 py-1" placeholder="Name"
                value={v.name} onChange={(e)=>patchVariant(i,{name:e.target.value})}/>
              <input className="border rounded px-2 py-1" placeholder="Subject"
                value={v.subject||""} onChange={(e)=>patchVariant(i,{subject:e.target.value})}/>
              <select className="border rounded px-2 py-1" value={v.channel||"sms"}
                onChange={(e)=>patchVariant(i,{channel:e.target.value as any})}>
                <option value="sms">SMS</option>
                <option value="email">Email</option>
              </select>
              <input type="number" className="border rounded px-2 py-1" placeholder="Timing (min)"
                value={v.timing_min ?? 0} onChange={(e)=>patchVariant(i,{timing_min:Number(e.target.value)})}/>
            </div>
          ))}
          <div className="flex gap-2">
            <button className="px-3 py-1 rounded bg-gray-100" onClick={()=>setVariants(v=>[...v,{name:`V${v.length+1}`}])}>+ Variant</button>
            <button className="px-3 py-2 rounded bg-blue-600 text-white" onClick={save}>Save / Upsert</button>
          </div>
        </div>
      </div>

      <div>
        <div className="font-medium mb-2">Saved experiments</div>
        <div className="rounded-xl border bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b">
                <th className="p-2">Name</th>
                <th className="p-2">Status</th>
                <th className="p-2">Variants</th>
                <th className="p-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {list.map((e)=>(
                <tr key={e.id} className="border-t">
                  <td className="p-2">{e.name}</td>
                  <td className="p-2">{e.status}</td>
                  <td className="p-2">{Object.keys(e.variants||{}).join(", ")}</td>
                  <td className="p-2">{(e.created_at||"").toString().replace("T"," ").replace("Z","")}</td>
                </tr>
              ))}
              {!list.length && <tr><td className="p-3 text-gray-500" colSpan={4}>No experiments yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="text-sm">See impact in <a className="text-blue-600 underline" href="/admin/analytics">Analytics</a>.</div>
    </div>
  );
}
