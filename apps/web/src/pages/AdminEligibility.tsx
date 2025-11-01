import { useEffect, useState } from "react";

export default function AdminEligibility() {
  const [data, setData] = useState<any>(null);
  const appt = new URLSearchParams(window.location.search).get("appointment_id") || "1";
  useEffect(() => {
    fetch(`/v1/admin/billing/eligibility?appointment_id=${appt}`)
      .then(r => r.json())
      .then(setData);
  }, [appt]);
  return (
    <div style={{ padding: 24 }}>
      <h2>Eligibility Detail</h2>
      {!data?.eligibility ? <p>No record.</p> : <pre>{JSON.stringify(data.eligibility, null, 2)}</pre>}
    </div>
  );
}
