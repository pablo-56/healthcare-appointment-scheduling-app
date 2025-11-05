import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../lib/fetcher";

export default function Book() {
  // default reason text
  const [reason, setReason] = useState("annual physical");

  // default preferred time = now + 1h, formatted for <input type="datetime-local">
  const [when, setWhen] = useState<string>(() =>
    new Date(Date.now() + 3600_000).toISOString().slice(0, 16)
  );

  // user messages (errors or small tips)
  const [msg, setMsg] = useState("");

  // disable button only while request is in flight
  const [loading, setLoading] = useState(false);

  const nav = useNavigate();

  async function submit() {
    setMsg("");
    setLoading(true);
    try {
      // 1) Prepare payload for the agent/intake endpoint
      //    - we pass 'reason' and the preferred 'when' (as ISO)
      //    - the orchestrator will select a slot and book behind the scenes
      const payload = {
        reason,
        when: new Date(when).toISOString(), // convert local -> ISO UTC
        source_channel: "web",
        // If your API uses session → patient_id comes from server.
        // If you want to force a dev patient id, uncomment:
        // context: { patient_id: 1 },
      };

      // 2) Call the orchestrator
      //    /v1/agents/scheduling/intake returns { appointment_id } on success
      const data = await api("/v1/agents/scheduling/intake", {
        method: "POST",
        body: JSON.stringify(payload),
        // fetcher.ts automatically sets X-Purpose-Of-Use for POST = TREATMENT
      });

      // 3) If the agent didn't give us an appointment_id, treat as "no slots"
      if (!data?.appointment_id) {
        throw new Error("No slots available; try another time or Telehealth.");
      }

      // 4) Success → go to confirm page (query param form kept to match your repo)
      nav(`/confirm?aid=${data.appointment_id}`);
    } catch (e: any) {
      // Network errors or 4xx/5xx bubble up as Error(e.message) from fetcher.ts
      const txt = e?.message || "Failed to fetch";
      const notFoundMsg = /404|No slots/i.test(txt)
        ? "No slots available; try another time or Telehealth."
        : txt;
      setMsg(notFoundMsg);
    } finally {
      setLoading(false); // keep button enabled so user can retry
    }
  }

  return (
    <div className="p-6 max-w-xl">
      <h2 className="text-xl font-semibold mb-4">Book an appointment</h2>

      {/* Reason for visit */}
      <label className="block mb-2">Reason for visit</label>
      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="border p-2 w-full mb-4"
        rows={2}
      />

      {/* Preferred time */}
      <label className="block mb-2">Preferred time</label>
      <input
        type="datetime-local"
        value={when}
        onChange={(e) => setWhen(e.target.value)}
        className="border p-2 w-full mb-4"
      />

      {/* Actions */}
      <div className="space-x-2">
        <button disabled={loading} onClick={submit} className="border px-3 py-1">
          {loading ? "Booking..." : "Book"}
        </button>
        <Link to="/" className="border px-3 py-1">
          Cancel
        </Link>
      </div>

      {/* Errors / guidance */}
      {msg && <p className="text-red-400 mt-3">{msg}</p>}
    </div>
  );
}
