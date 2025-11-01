import { useState } from "react";

export default function Consent() {
    const [appointmentId, setAppointmentId] = useState<number>(1);
    const [email, setEmail] = useState("me@example.com");
    const [name, setName] = useState("Jane Patient");

    async function requestSignature() {
        const r = await fetch("/api/v1/signature/requests", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ appointment_id: appointmentId, signer_name: name, email }),
        });
        const data = await r.json();
        alert(`Signature request created: ${data.request_id}\nNow simulating webhook…`);
        // Simulate the provider posting the webhook
        const payload = { request_id: data.request_id, appointment_id: appointmentId, signer_name: name, signer_ip: "127.0.0.1" };
        const raw = JSON.stringify(payload);
        const sig = await (await fetch("/tools/hmac", { // if you don't have, compute in terminal and paste
            method: "POST", body: raw
        })).text();
        await fetch("/api/v1/signature/webhook", { method: "POST", headers: { "Content-Type": "application/json", "X-Signature": sig }, body: raw });
        alert("Webhook delivered!");
    }

    return (
        <div className="p-6">
            <h1 className="text-xl mb-4">Consent (mock)</h1>
            <div className="space-y-2">
                <input className="border p-1" value={appointmentId} onChange={e => setAppointmentId(parseInt(e.target.value || "1", 10))} />
                <input className="border p-1" value={name} onChange={e => setName(e.target.value)} />
                <input className="border p-1" value={email} onChange={e => setEmail(e.target.value)} />
                <button className="border px-3 py-1" onClick={requestSignature}>Request & Simulate Webhook</button>
            </div>
        </div>
    );
}
