import { useEffect, useState } from "react";

type TaskItem = { id: number; status: string; payload_json: any; created_at?: string };

export default function AdminTasks() {
  const [items, setItems] = useState<TaskItem[]>([]);
  useEffect(() => {
    fetch("/v1/admin/tasks").then(r => r.json()).then(d => setItems(d.items || []));
  }, []);
  return (
    <div style={{ padding: 24 }}>
      <h2>Eligibility Follow-ups</h2>
      {items.length === 0 && <p>No follow-up tasks.</p>}
      <ul>
        {items.map(t => (
          <li key={t.id}>
            <code>#{t.id}</code> – {t.status} – {t.created_at || ""}
            <pre>{JSON.stringify(t.payload_json, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
