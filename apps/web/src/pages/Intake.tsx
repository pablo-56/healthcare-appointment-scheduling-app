import { useEffect, useState } from "react";

export default function Intake() {
    const [appointmentId, setAppointmentId] = useState<number>(1);
    const [schema, setSchema] = useState<any>(null);
    const [answers, setAnswers] = useState<any>({});

    async function loadSchema(id: number) {
        const res = await fetch(`/api/v1/intake/forms?appointment_id=${id}`);
        const data = await res.json();
        setSchema(data.schema);
    }

    useEffect(() => { loadSchema(appointmentId); }, [appointmentId]);

    async function submit() {
        await fetch(`/api/v1/intake/forms/${appointmentId}/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Purpose-Of-Use": "TREATMENT" },
            body: JSON.stringify({ answers }),
        });
        alert("Submitted! A PDF will appear soon in Documents.");
    }

    return (
        <div className="p-6">
            <h1 className="text-xl mb-4">Intake for appointment #{appointmentId}</h1>
            <div className="mb-2">
                <input
                    className="border p-2"
                    type="number"
                    value={appointmentId}
                    onChange={e => setAppointmentId(parseInt(e.target.value || "1", 10))}
                />
            </div>
            {schema ? (
                <div className="space-y-2">
                    {Object.keys(schema.properties || {}).map((k) => (
                        <div key={k}>
                            <label className="mr-2">{k}</label>
                            <input
                                className="border p-1"
                                onChange={(e) => setAnswers({ ...answers, [k]: e.target.value })}
                            />
                        </div>
                    ))}
                    <button className="border px-3 py-1" onClick={submit}>Submit</button>
                </div>
            ) : <div>Loading schema…</div>}
        </div>
    );
}
