import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/fetcher";

type Case = { id: number; encounter_id: string; appointment_id?: number; status: string; total_cents?: number; updated_at?: string };

/**
 * Worklist for coders/billers.
 * - GET /v1/billing/cases
 * - Click → /billing/claims/:id
 * - If empty: show "No active cases"
 */
export default function BillingCases() {
  const [items, setItems] = useState<Case[]>([]);
  const [err, setErr] = useState("");
  const nav = useNavigate();

  async function load() {
    setErr("");
    try {
      // Use PoU PAYMENT/OPERATIONS for revenue-cycle pages
      const data = await api("/v1/billing/cases", { method: "GET", pou: "OPERATIONS" });
      setItems(data?.items || []);
    } catch (e:any) {
      setErr(e.message || "Failed to load cases");
    }
  }
  useEffect(() => { load(); }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-3">Billing Cases</h1>
      {err && <div className="text-red-600 text-sm mb-2">{err}</div>}

      {!items.length && <div className="text-gray-500">No active cases</div>}

      <ul className="space-y-2">
        {items.map(c => (
          <li
            key={c.id}
            className="border rounded p-2 bg-white cursor-pointer hover:bg-gray-50"
            onClick={() => nav(`/billing/claims/${c.id}`)}
          >
            <div className="font-medium">Case #{c.id} — {c.status}</div>
            <div className="text-xs text-gray-500">
              {c.encounter_id} • {c.total_cents ? `$${(c.total_cents/100).toFixed(2)}` : "—"} {c.updated_at ? `• ${new Date(c.updated_at).toLocaleString()}` : ""}
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-4">
        <Link to="/" className="underline">Home</Link>
      </div>
    </div>
  );
}
