import { useState } from "react";

export default function AdminCompliancePIA() {
  const [url, setUrl] = useState<string>("");
  const [err, setErr] = useState("");

  async function gen() {
    setErr(""); setUrl("");
    try {
      const res = await fetch("/v1/compliance/pia-pack", { headers: { "X-Purpose-Of-Use": "OPERATIONS" }});
      if (!res.ok) throw new Error(await res.text());
      const j = await res.json();
      setUrl(j.artifact_url);
    } catch (e:any) {
      setErr(String(e));
    }
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Compliance &rsaquo; PIA Pack</h1>
      <button onClick={gen} className="px-3 py-2 bg-black text-white rounded">Generate</button>
      {err && <div className="text-red-600">{err}</div>}
      {url && <div><a download="pia_pack.html" href={url} className="underline text-blue-600">Download PIA (HTML)</a></div>}
    </div>
  );
}
