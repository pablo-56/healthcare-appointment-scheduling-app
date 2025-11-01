import { useEffect, useState } from "react";

type QueueItem = {
  appointment_id: number;
  status: "BOOKED" | "ARRIVED" | string;
  reason?: string;
  fhir_appointment_id?: string;
  start_at?: string;
  end_at?: string;
  minutes_to_start?: number | null;
  late?: boolean;
  no_show?: boolean;
  patient?: {
    id?: number;
    first_name?: string;
    last_name?: string;
    email?: string;
    phone?: string;
  };
};

export default function Queue() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");

  async function load() {
    const res = await fetch("/v1/ops/queue");
    const data = await res.json();
    setItems(data.items || []);
    setLastUpdated(data.now || new Date().toISOString());
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Front Desk Queue</h1>
        <div className="text-sm opacity-70">Updated: {new Date(lastUpdated).toLocaleTimeString()}</div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left border">
          <thead className="bg-gray-50">
            <tr>
              <th className="p-2 border">Appt ID</th>
              <th className="p-2 border">Patient</th>
              <th className="p-2 border">Start</th>
              <th className="p-2 border">Status</th>
              <th className="p-2 border">Late</th>
              <th className="p-2 border">No-show</th>
              <th className="p-2 border">Reason</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.appointment_id} className="border-b">
                <td className="p-2 border">{it.appointment_id}</td>
                <td className="p-2 border">
                  {it.patient?.first_name} {it.patient?.last_name}
                  <div className="text-xs opacity-70">{it.patient?.email}</div>
                </td>
                <td className="p-2 border">
                  {it.start_at ? new Date(it.start_at).toLocaleTimeString() : "-"}
                </td>
                <td className="p-2 border">{it.status}</td>
                <td className="p-2 border">{it.late ? "Yes" : ""}</td>
                <td className="p-2 border">{it.no_show ? "Yes" : ""}</td>
                <td className="p-2 border">{it.reason || ""}</td>
              </tr>
            ))}
            {!items.length && (
              <tr><td className="p-3 text-center" colSpan={7}>No items.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
