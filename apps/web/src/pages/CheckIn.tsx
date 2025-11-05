import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/fetcher";

/**
 * Check-in collects the appointment id, lets the user confirm their data,
 * and (optionally) capture a couple of vitals in kiosk/FOH scenarios.
 * On success, we show the queue position and, once opened, deep-link
 * to the live visit summary (/portal/summary/:encounterId).
 */
export default function CheckIn() {
  const [search] = useSearchParams();
  const [appointmentId, setAppointmentId] = useState("");
  const [email, setEmail] = useState("");          // optional identity for audit
  const [confirm, setConfirm] = useState(false);
  const [msg, setMsg] = useState("");
  const [result, setResult] = useState<any>(null);

  // quick, optional vitals
  const [hr, setHr] = useState<string>("");
  const [temp, setTemp] = useState<string>("");

  // ---- NEW: prefill from ?aid= ------------------------------------------------
  useEffect(() => {
    const aid = search.get("aid");
    if (aid) setAppointmentId(aid);
  }, [search]);

  async function submit() {
    setMsg("");
    setResult(null);
    try {
      if (!appointmentId) throw new Error("Provide an appointment id");
      if (!confirm) throw new Error("Please confirm your information is correct");

      const payload: any = {
        appointment_id: Number(appointmentId),
        patient_email: email || undefined,
        vitals: {
          heart_rate: hr ? Number(hr) : undefined,
          temperature_c: temp ? Number(temp) : undefined,
        },
      };

      const data = await api("/v1/checkin", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      // expect { position: number, encounter_id?: string, message: "Checked in", ... }
      setResult(data);
    } catch (e: any) {
      setMsg(e.message || "Could not check in. If you are late, please reschedule.");
    }
  }

  return (
    <div className="p-6 max-w-md">
      <h2 className="text-xl font-semibold mb-4">Check-in</h2>

      <input
        className="border p-2 w-full mb-3"
        placeholder="Appointment ID"
        value={appointmentId}
        onChange={(e) => setAppointmentId(e.target.value)}
      />

      {/* optional email identity for audit trail */}
      <input
        className="border p-2 w-full mb-3"
        placeholder="Email (optional)"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      {/* optional quick vitals */}
      <div className="flex gap-2 mb-3">
        <input
          className="border p-2 w-full"
          placeholder="Heart rate (bpm)"
          value={hr}
          onChange={(e) => setHr(e.target.value)}
        />
        <input
          className="border p-2 w-full"
          placeholder="Temp (°C)"
          value={temp}
          onChange={(e) => setTemp(e.target.value)}
        />
      </div>

      <label className="flex items-center gap-2 mb-4">
        <input type="checkbox" checked={confirm} onChange={(e)=>setConfirm(e.target.checked)} />
        My info is correct.
      </label>

      <div className="space-x-2">
        <button onClick={submit} className="border px-3 py-1">Submit</button>
        <Link to="/book" className="border px-3 py-1">Reschedule</Link>
      </div>

      {msg && <p className="text-red-400 mt-3">{msg}</p>}

      {result && (
        <div className="mt-4">
          <p>Queue position: {result.position ?? "—"}</p>
          {result.encounter_id && (
            <p>
              When called, you’ll see your{" "}
              <Link className="underline" to={`/portal/summary/${result.encounter_id}`}>
                visit summary
              </Link>.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
