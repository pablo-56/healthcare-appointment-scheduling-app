// apps/web/src/pages/OpsEscalations.tsx
import { useEffect, useState } from "react";
import { listTasks } from "../api";

export default function OpsEscalations() {
  const [items, setItems] = useState<any[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        const data = await listTasks({ type: "care_escalation", status: "open" });
        setItems(data.items || []);
      } catch (e: any) {
        setErr(e.message || "Failed");
      }
    })();
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-xl font-bold mb-4">Open Care Escalations</h1>
      {err && <div className="text-red-600">{err}</div>}
      <ul className="space-y-3">
        {items.map((t) => (
          <li key={t.id} className="rounded-xl p-4 shadow bg-white/5">
            <div className="text-sm opacity-70">#{t.id} • {t.status}</div>
            <div className="font-semibold">{t.payload_json?.title || t.type}</div>
            <pre className="text-xs opacity-80 overflow-auto">{JSON.stringify(t.payload_json, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
