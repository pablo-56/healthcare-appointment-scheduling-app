import { useState } from "react";

export default function AdminComplianceRetention() {
  const [out, setOut] = useState<any>(null);
  const [err, setErr] = useState("");

  async function run() {
    setErr("");
    try {
      const res = await fetch("/v1/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Purpose-Of-Use": "OPERATIONS" },
        body: JSON.stringify({ type: "retention.run_now", payload: {}, assignee: "system", status: "open" })
      });
      if (!res.ok) throw new Error(await res.text());
      setOut(await res.json());
    } catch (e:any) {
      setErr(String(e));
    }
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Compliance &rsaquo; Retention</h1>
      <p className="text-sm text-gray-400">Documents blobs older than RETENTION_DAYS are nulled, audit trimmed at 2× window. You can also rely on the nightly schedule.</p>
      <button onClick={run} className="px-3 py-2 bg-black text-white rounded">Run now</button>
      {err && <div className="text-red-600">{err}</div>}
      {out && <pre className="text-xs">{JSON.stringify(out,null,2)}</pre>}
    </div>
  );
}
