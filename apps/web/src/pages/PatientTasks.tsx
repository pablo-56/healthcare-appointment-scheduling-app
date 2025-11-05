import { useEffect, useState } from "react";
import { api } from "../lib/fetcher";
import { Link } from "react-router-dom";

type Task = { id:number; type?:string; status:"open"|"in_progress"|"done"|"canceled"; payload_json?:any; assignee?:string; created_at?:string };

export default function PatientTasks() {
  const [rows, setRows] = useState<Task[]>([]);
  const [msg, setMsg] = useState("");

  async function load() {
    try {
      // Backend returns { items: [...] }
      const data = await api("/v1/tasks?me=true", { method: "GET", pou: "OPERATIONS" });
      setRows(data?.items || []);
    } catch (e:any){
      setMsg(e.message || "Failed to load");
    }
  }
  useEffect(() => { load(); }, []);

  async function complete(id:number) {
    try {
      await api(`/v1/tasks/${id}/complete`, { method:"POST", pou: "OPERATIONS" });
      // optimistic update
      setRows((r)=>r.map(t=>t.id===id?{...t,status:"done"}:t));
    } catch (e:any) {
      setMsg(e.message || "Could not complete task");
    }
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-3">Your tasks</h2>
      {rows.length === 0 && <p className="text-gray-400 mb-3">No tasks at the moment.</p>}
      <ul className="space-y-2">
        {rows.map(t => (
          <li key={t.id} className="border p-2 flex items-center justify-between">
            <div>
              <div className="font-medium">{t.payload_json?.title || t.type || `Task #${t.id}`}</div>
              <div className="text-xs text-gray-400">
                {t.payload_json?.kind || ""} {t.created_at ? `• created ${new Date(t.created_at).toLocaleString()}` : ""}
              </div>
            </div>
            <div className="space-x-2">
              {t.status !== "done" && <button onClick={()=>complete(t.id)} className="border px-3 py-1">Complete</button>}
            </div>
          </li>
        ))}
      </ul>
      {msg && <p className="text-red-400 mt-3">{msg}</p>}
      <div className="mt-4 space-x-2">
        <Link to="/" className="border px-3 py-1">Home</Link>
        <Link to="/portal/follow-up" className="border px-3 py-1">Book follow-up</Link>
      </div>
    </div>
  );
}
