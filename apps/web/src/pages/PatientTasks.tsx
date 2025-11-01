// apps/web/src/pages/PatientTasks.tsx
import { useEffect, useState } from "react";

type Task = { id: number; payload_json: any };

const PHQ_OPTIONS = [
  { label: "Not at all", value: 0 },
  { label: "Several days", value: 1 },
  { label: "More than half the days", value: 2 },
  { label: "Nearly every day", value: 3 },
];

const PHQ_QUESTIONS = [
  "Little interest or pleasure in doing things",
  "Feeling down, depressed, or hopeless",
  "Trouble falling/staying asleep, or sleeping too much",
  "Feeling tired or having little energy",
  "Poor appetite or overeating",
  "Feeling bad about yourself—or that you’re a failure",
  "Trouble concentrating on things",
  "Moving/speaking slowly or being fidgety/restless",
  "Thoughts of being better off dead or self-harm",
];

export default function PatientTasks() {
  // In real app, derive from session; for demo we use 1
  const [patientId] = useState<number>(1);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [answers, setAnswers] = useState<number[]>(
    Array(PHQ_QUESTIONS.length).fill(0)
  );
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string>("");

  async function load() {
    setErr("");
    const res = await fetch(
      `/v1/tasks?type=pro_reminder&patient_id=${patientId}`,
      { headers: { "X-Purpose-Of-Use": "TREATMENT" } }
    );
    const data = await res.json();
    setTasks(data.items || []);
  }

  useEffect(() => { load(); }, []);

  async function submitPHQ9() {
    setErr("");
    setResult(null);
    const res = await fetch(`/v1/pros/phq9`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Purpose-Of-Use": "TREATMENT",
      },
      body: JSON.stringify({
        patient_id: patientId,
        answers,
        language: "en",
      }),
    });
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setErr(j.detail || "Submit failed");
      return;
    }
    const j = await res.json();
    setResult(j);
    // refresh reminders (you might auto-close them server-side later)
    load();
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-xl font-bold mb-4">Your Tasks</h1>
      <div className="mb-6">
        {tasks.length === 0 ? (
          <p>No open reminders.</p>
        ) : (
          <ul className="list-disc pl-6">
            {tasks.map((t) => (
              <li key={t.id}>Complete {t.payload_json?.instrument?.toUpperCase()} survey</li>
            ))}
          </ul>
        )}
      </div>

      <h2 className="font-semibold mb-2">PHQ-9</h2>
      <div className="space-y-4">
        {PHQ_QUESTIONS.map((q, qi) => (
          <div key={qi}>
            <div className="mb-1">{qi + 1}. {q}</div>
            <div className="flex gap-3">
              {PHQ_OPTIONS.map((o) => (
                <label key={o.value} className="flex items-center gap-1">
                  <input
                    type="radio"
                    name={`q${qi}`}
                    value={o.value}
                    checked={answers[qi] === o.value}
                    onChange={() => {
                      const next = answers.slice();
                      next[qi] = o.value;
                      setAnswers(next);
                    }}
                  />
                  <span>{o.label}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
      <button
        onClick={submitPHQ9}
        className="mt-4 px-4 py-2 rounded bg-blue-600 text-white"
      >
        Submit PHQ-9
      </button>

      {err && <p className="text-red-600 mt-3">{err}</p>}
      {result && (
        <div className="mt-4 p-3 rounded border">
          <div>Score: <b>{result.score}</b></div>
          {result.escalated_task_id ? (
            <div className="text-amber-700">A nurse has been alerted.</div>
          ) : (
            <div className="text-green-700">Thanks for completing the survey.</div>
          )}
        </div>
      )}
    </div>
  );
}
