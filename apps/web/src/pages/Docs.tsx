import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { api } from "../lib/fetcher";
import { getAppointment } from "../lib/api";

export default function Docs() {
  const [search] = useSearchParams();
  const appt = search.get("appt") || "";
  const [docs, setDocs] = useState<any[]>([]);
  const [msg, setMsg] = useState("");
  const [isDayOf, setIsDayOf] = useState(false); // <-- show Check-in only if day-of

  useEffect(() => {
    (async () => {
      try {
        // Load documents for this appointment
        const data = await api(`/v1/documents?appointment_id=${appt}`);
        setDocs(data?.documents || []);
      } catch (e: any) {
        setMsg(e.message || "Failed to load documents");
      }
    })();
  }, [appt]);

  useEffect(() => {
    (async () => {
      // Optional: determine if this is the same day as the appointment (local time)
      try {
        if (!appt) return;
        const r = await getAppointment(Number(appt));
        const start = r?.appointment?.start_at ? new Date(r.appointment.start_at) : null;
        if (!start) return;
        const now = new Date();
        const sameDay =
          start.getFullYear() === now.getFullYear() &&
          start.getMonth() === now.getMonth() &&
          start.getDate() === now.getDate();
        setIsDayOf(sameDay);
      } catch {
        // If we can’t fetch appointment, just don’t show the day-of link
      }
    })();
  }, [appt]);

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Your documents</h2>

      {docs.length === 0 && <p className="text-gray-400 mb-4">No documents available yet.</p>}

      <ul className="list-disc pl-5">
        {docs.map((d) => (
          <li key={d.id}>
            <a className="underline" href={d.url} target="_blank" rel="noreferrer">
              {d.title || d.kind}
            </a>
          </li>
        ))}
      </ul>

      <div className="mt-4 space-x-2">
        {isDayOf ? (
          <Link to="/check-in" className="border px-3 py-1">Check-in</Link>
        ) : (
          <Link to="/" className="border px-3 py-1">Home</Link>
        )}
      </div>

      {msg && <p className="text-red-400 mt-3">{msg}</p>}
    </div>
  );
}
