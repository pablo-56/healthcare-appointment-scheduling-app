import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/fetcher";
import { usePoll } from "../lib/usePoll";

export default function PortalSummary() {
  const { encounterId } = useParams();
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const data = await api(`/v1/encounters/${encounterId}/summary`);
      setSummary(data);
      setLoading(false);
    } catch {
      setLoading(true); // keep polling if not ready
    }
  }
  useEffect(() => { load(); }, [encounterId]);
  usePoll(load, 3000, loading); // “We’re finishing your note”

  if (loading) return <div className="p-6">Preparing your summary…</div>;

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-3">Visit summary</h2>
      <pre className="bg-black/20 p-3 rounded">{JSON.stringify(summary?.note, null, 2)}</pre>
      <div className="mt-4 space-x-2">
        <Link to="/portal/follow-up" className="border px-3 py-1">Follow-up</Link>
        <Link to="/portal/tasks" className="border px-3 py-1">Tasks</Link>
      </div>
    </div>
  );
}
