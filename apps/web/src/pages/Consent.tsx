import { useEffect, useState } from "react";
import { useParams, useNavigate, Link, useSearchParams } from "react-router-dom";
import { api } from "../lib/fetcher";
import { usePoll } from "../lib/usePoll";

export default function Consent() {
  const { requestId } = useParams();
  const [search] = useSearchParams();
  const apptFromQuery = search.get("appt") || "";

  const [status, setStatus] = useState("PENDING");
  const [msg, setMsg] = useState("");
  const [appt, setAppt] = useState<string>(apptFromQuery);
  const [retrying, setRetrying] = useState(false);

  const nav = useNavigate();

  async function check() {
    try {
      const data = await api(`/v1/signature/requests/${requestId}`);
      setStatus(data?.status || "PENDING"); // SIGNED | PENDING
      if (!appt && data?.appointment_id) setAppt(String(data.appointment_id));
      if (data?.status === "SIGNED") nav(`/docs?appt=${appt || data.appointment_id}`);
    } catch (e: any) {
      setMsg(e.message || "Failed to check status");
    }
  }

  // Allow the user to retry creating the signature request if provider failed externally
  async function retry() {
    setMsg("");
    setRetrying(true);
    try {
      const apptId = Number(appt || 0);
      if (!apptId) throw new Error("Missing appointment id");
      // Recreate request (this mirrors intake submission behavior)
      const r = await api("/v1/signature/requests", {
        method: "POST",
        body: JSON.stringify({
          appointment_id: apptId,
          signer_name: "Patient",
          email: "patient@example.com",
        }),
        pou: "OPERATIONS",
      });
      // Move to the new request page so polling starts fresh
      if (r?.request_id) {
        return nav(`/consent/${r.request_id}?appt=${apptId}`);
      }
      setMsg("Could not start a new signature request. Please try again.");
    } catch (e: any) {
      setMsg(e.message || "Could not retry. Please contact support.");
    } finally {
      setRetrying(false);
    }
  }

  useEffect(() => { check(); }, []);                 // first check immediately
  usePoll(check, 3000, status === "PENDING");        // poll every 3s while pending

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-2">Consent & e-signature</h2>
      <p className="mb-2">Status: {status}</p>
      {msg && <p className="text-red-400 mb-2">{msg}</p>}

      <p className="text-sm text-gray-400 mb-4">
        Please sign the consent sent to you. We’ll take you to your documents as soon as it’s signed.
        If your e-signature provider fails, you can try again below, or contact support.
      </p>

      <div className="space-x-2">
        <button onClick={check} className="border px-3 py-1">Check again</button>
        <button onClick={retry} disabled={retrying} className="border px-3 py-1">
          {retrying ? "Starting…" : "Try again"}
        </button>
        {/* Keep docs link visible even on errors */}
        <Link to={`/docs?appt=${appt}`} className="border px-3 py-1">View documents</Link>
      </div>
    </div>
  );
}
