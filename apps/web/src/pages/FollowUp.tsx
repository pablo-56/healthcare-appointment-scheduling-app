// apps/web/src/pages/FollowUp.tsx
// Phase 7: simple follow-up booking form that reuses POST /v1/appointments

import { useState } from "react";

export default function FollowUp() {
  const [email, setEmail] = useState("me@example.com");
  const [reason, setReason] = useState("Follow-up after recent visit");
  const [start, setStart] = useState(""); // datetime-local value (local time)
  const [msg, setMsg] = useState("");

  async function submit() {
    setMsg("");
    try {
      if (!start) throw new Error("Please choose a start time");
      // Convert local datetime-local to ISO string
      const startDate = new Date(start);
      const endDate = new Date(startDate.getTime() + 20 * 60 * 1000); // +20 min

      const payload = {
        patient_email: email,
        reason,
        start: startDate.toISOString(),
        end: endDate.toISOString(),
        slot_id: "followup-auto",
        source_channel: "portal",
      };

      const res = await fetch(`${import.meta.env.VITE_API_BASE}/v1/appointments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Purpose-Of-Use": "TREATMENT",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      const data = await res.json();
      setMsg(`Booked follow-up! Appointment #${data.id}`);
    } catch (e: any) {
      setMsg(`Error: ${e.message || String(e)}`);
    }
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-3xl mb-3">Book a Follow-up</h1>

      <div className="grid gap-3 max-w-xl">
        <label className="grid gap-1">
          <span>Email</span>
          <input className="p-2 rounded bg-zinc-900 border border-zinc-700"
                 value={email} onChange={e => setEmail(e.target.value)} />
        </label>

        <label className="grid gap-1">
          <span>Reason</span>
          <input className="p-2 rounded bg-zinc-900 border border-zinc-700"
                 value={reason} onChange={e => setReason(e.target.value)} />
        </label>

        <label className="grid gap-1">
          <span>Start time</span>
          <input type="datetime-local"
                 className="p-2 rounded bg-zinc-900 border border-zinc-700"
                 value={start} onChange={e => setStart(e.target.value)} />
        </label>

        <button onClick={submit}
                className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-700 w-fit">
          Book follow-up
        </button>

        {msg && <div className="mt-2">{msg}</div>}
      </div>
    </div>
  );
}
