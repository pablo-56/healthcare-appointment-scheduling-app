import { useEffect, useState } from "react";
import { complianceGet, compliancePost } from "../lib/api";

// Kicks the PIA job; shows request_id; polls a status API.
// If Celery is down, backend runs inline and still returns ok + request_id.

export default function AdminCompliancePIA() {
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [reqId, setReqId] = useState<number | null>(null);
  const [status, setStatus] = useState<string>("");

  async function run(kind: "pia-pack" | "export" | "erasure") {
    setErr(""); setMsg(""); setStatus("");
    setReqId(null);
    try {
      const path = kind === "pia-pack" ? "/v1/compliance/pia-pack"
                 : kind === "export"   ? "/v1/compliance/export"
                 :                       "/v1/compliance/erasure";
      const r = await compliancePost<{ok:boolean; request_id:number}>(path, {});
      setReqId(r.request_id);
      setMsg(`${kind} queued (id ${r.request_id}). Polling status…`);
    } catch (e: any) {
      setErr(e.message || String(e));
    }
  }

  async function poll() {
    if (!reqId) return;
    try {
      const r = await complianceGet<{id:number; kind:string; status:string; meta?:any}>(`/v1/compliance/requests/${reqId}`);
      setStatus(r.status || "");
      if (r.status === "DONE") setMsg(`Request ${r.id} finished.`);
      if (r.status === "ERROR") setErr(`Request ${r.id} failed.`);
    } catch (e:any) {
      // Don’t clear the row on failures: keep showing the id & allow retry/reload.
      setErr(e.message || "Polling failed");
    }
  }

  // poll every 3s while pending
  useEffect(() => {
    if (!reqId) return;
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reqId]);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Compliance — PIA & Requests</h1>
      <div className="text-xs text-gray-500">
        <a className="text-blue-600 underline" href="/admin/compliance/audit">Audit</a> •
        <a className="text-blue-600 underline" href="/admin/compliance/pia">PIA/DSR</a> •
        <a className="text-blue-600 underline" href="/admin/compliance/retention">Retention</a>
      </div>

      {err && <div className="text-red-600 text-sm">{err}</div>}
      {msg && <div className="text-green-700 text-sm">{msg}</div>}

      <div className="flex gap-2">
        <button className="px-3 py-2 rounded bg-gray-800 text-white" onClick={()=>run("pia-pack")}>
          Generate PIA Pack (PDF)
        </button>
        <button className="px-3 py-2 rounded bg-gray-100" onClick={()=>run("export")}>
          Data Export (DSR)
        </button>
        <button className="px-3 py-2 rounded bg-rose-600 text-white" onClick={()=>run("erasure")}>
          Erasure Request
        </button>
      </div>

      {reqId && (
        <div className="text-sm">
          Request: <b>#{reqId}</b> • Status: <b>{status || "PENDING…"}</b> •{" "}
          <a className="underline" href="/admin/tasks">View tasks</a>
        </div>
      )}
    </div>
  );
}
