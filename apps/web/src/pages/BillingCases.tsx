// apps/web/src/pages/BillingCases.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

/**
 * Simple worklist that queries /v1/coding/cases (PAYMENT/OPERATIONS).
 * Shows NEW/SUBMITTED/DENIED/REJECTED; PAID is hidden.
 */
export default function BillingCases() {
  const [items, setItems] = useState<any[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    const run = async () => {
      setErr("");
      try {
        const res = await fetch(`${import.meta.env.VITE_API_BASE}/v1/coding/cases`, {
          headers: { "X-Purpose-Of-Use": "PAYMENT" },
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
        const js = await res.json();
        setItems(js.items || []);
      } catch (e: any) {
        setErr(String(e));
      }
    };
    run();
  }, []);

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Billing Worklist</h1>
      {err && <div className="text-red-400">Error: {err}</div>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b border-neutral-700">
            <th className="py-2">ID</th>
            <th>Encounter</th>
            <th>Status</th>
            <th>Total</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id} className="border-b border-neutral-800">
              <td className="py-2">
                <Link className="underline" to={`/billing/claims/${r.id}`}>#{r.id}</Link>
              </td>
              <td>{r.encounter_id}</td>
              <td>{r.status}</td>
              <td>${((r.total_cents || 0) / 100).toFixed(2)}</td>
              <td>{new Date(r.updated_at).toLocaleString()}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td className="py-6" colSpan={5}>No open cases.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
