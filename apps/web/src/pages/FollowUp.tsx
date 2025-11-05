import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../lib/fetcher";

export default function FollowUp() {
  const nav = useNavigate();
  const [reason, setReason] = useState("follow-up visit");
  const [when, setWhen] = useState<string>(() => new Date(Date.now() + 7*24*3600_000).toISOString().slice(0,16));
  const [msg, setMsg] = useState("");

  async function submit() {
    setMsg("");
    try {
      const data = await api("/v1/agents/scheduling/intake", {
        method: "POST",
        body: JSON.stringify({ reason, when: new Date(when).toISOString() })
      });
      if (!data?.appointment_id) throw new Error("No slots available; try another time.");
      nav(`/confirm?aid=${data.appointment_id}`);
    } catch (e: any) {
      setMsg(e.message || "Failed to book");
    }
  }

  return (
    <div className="p-6 max-w-xl">
      <h2 className="text-xl font-semibold mb-4">Book a follow-up</h2>
      <textarea className="border p-2 w-full mb-3" value={reason} onChange={(e)=>setReason(e.target.value)} />
      <input className="border p-2 w-full mb-3" type="datetime-local" value={when} onChange={(e)=>setWhen(e.target.value)} />
      <div className="space-x-2">
        <button onClick={submit} className="border px-3 py-1">Book</button>
        <Link to="/" className="border px-3 py-1">Cancel</Link>
      </div>
      {msg && <p className="text-red-400 mt-3">{msg}</p>}
    </div>
  );
}
