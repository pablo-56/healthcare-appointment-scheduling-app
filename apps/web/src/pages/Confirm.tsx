import { useEffect, useState } from "react";
import { useSearchParams, Link, useNavigate } from "react-router-dom";
import { getEligibility, getAppointment } from "../lib/api";

export default function Confirm() {
  const [search] = useSearchParams();
  const aid = Number(search.get("aid") || 0);

  // Optional: show appt details on this page (if present)
  const [appt, setAppt] = useState<any>(null);

  // Estimate + errors
  const [elig, setElig] = useState<any>(null);
  const [err, setErr] = useState("");

  // “Complete intake” button state
  const [going, setGoing] = useState(false);

  const nav = useNavigate();

  // ---- Optional: fetch appointment details to render the confirmation card
  useEffect(() => {
    if (!aid) return;
    (async () => {
      try {
        const res = await getAppointment(aid);   // { appointment: {...} }
        setAppt(res.appointment);
      } catch (e: any) {
        // don't block page if fetch fails; we still show the id and the button
        // but remember the error for debugging
        console.debug("load appt failed:", e?.message);
      }
    })();
  }, [aid]);

  // ---- Load basic estimate for display; ignore if not yet ready
  useEffect(() => {
    if (!aid) return;
    (async () => {
      try {
        const data = await getEligibility(aid);
        setElig(data.result);
      } catch (e: any) {
        setErr(e.message || "");
      }
    })();
  }, [aid]);

  // ---- When user clicks "Complete intake"
  async function goToIntake() {
    setErr("");
    setGoing(true);
    try {
      // Validate appointment exists (404 -> Not found)
      await getAppointment(aid);
      // Success → send to intake
      nav(`/intake/${aid}`);
    } catch (e: any) {
      const msg = String(e?.message || "");
      if (/404|not\s*found/i.test(msg)) {
        setErr("Not found");
      } else {
        setErr(msg || "Failed to fetch");
      }
    } finally {
      setGoing(false); // keep button enabled so user can retry
    }
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Appointment confirmed</h1>

      {!aid ? (
        <div className="text-red-500">Missing appointment id.</div>
      ) : (
        <div className="border p-3 rounded text-sm space-y-1">
          <div><b>Appointment ID:</b> {aid}</div>
          <div><b>Status:</b> {appt?.status || "BOOKED"}</div>
          {appt?.reason && <div><b>Reason:</b> {appt.reason}</div>}
          {appt?.start_at && <div><b>Start:</b> {new Date(appt.start_at).toLocaleString()}</div>}
          {appt?.end_at && <div><b>End:</b> {new Date(appt.end_at).toLocaleString()}</div>}
          {appt?.source_channel && <div><b>Source:</b> {appt.source_channel}</div>}
        </div>
      )}

      {/* Action: Complete intake */}
      <div className="flex gap-2">
        <button
          onClick={goToIntake}
          disabled={!aid || going}
          className="border px-3 py-1"
        >
          {going ? "Opening intake…" : "Complete intake"}
        </button>
        <Link to="/" className="underline">Back to Home</Link>
      </div>

      {/* If appointment is missing, show Not found + link back to /book */}
      {err === "Not found" && (
        <div className="text-red-500">
          Not found. <Link className="underline" to="/book">Back to book</Link>
        </div>
      )}
      {err && err !== "Not found" && <div className="text-red-500">{err}</div>}

      {/* Optional: show estimate when cached */}
      <div className="mt-2">
        <h2 className="text-lg font-semibold mb-1">Estimate</h2>
        {elig ? (
          <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto">
            {JSON.stringify(elig, null, 2)}
          </pre>
        ) : (
          <div className="text-sm text-gray-400">Calculating…</div>
        )}
      </div>
    </div>
  );
}
