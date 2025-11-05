import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "../lib/fetcher";

type JsonSchema = { properties?: Record<string, { title?: string; type?: string }>; required?: string[] };
type FormDef = { id: number; title: string; schema?: JsonSchema };

export default function Intake() {
  const { appointmentId } = useParams();
  const [forms, setForms] = useState<FormDef[]>([]);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [errors, setErrors] = useState<Record<string, string>>({}); // <-- field-level errors
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        // Load forms for this appointment
        const data = await api(`/v1/intake/forms?appointment_id=${appointmentId}`);
        // Backend returns { forms: [...] }. If not, fallback to a single generic form.
        const f = Array.isArray(data?.forms) && data.forms.length > 0
          ? data.forms
          : [{ id: 1, title: "Intake", schema: data?.schema || { properties: {} } }];
        setForms(f);
      } catch (e: any) {
        setMsg(e.message || "Failed to load forms");
      } finally {
        setLoading(false);
      }
    })();
  }, [appointmentId]);

  function onChange(formId: number, field: string, value: any) {
    const key = `${formId}.${field}`;
    setAnswers((prev) => ({ ...prev, [key]: value }));
    // Clear field-level error on edit
    setErrors((prev) => {
      if (!prev[key]) return prev;
      const { [key]: _, ...rest } = prev;
      return rest;
    });
  }

  async function submit() {
    setMsg("");
    setErrors({});
    try {
      // Submit all answers in one payload; server does validation and either:
      //  - returns { ok:false, errors:{...} } for validation errors (200 OK)
      //  - returns { ok:true, next:"consent"| "docs", request_id?, appointment_id }
      const res = await api(`/v1/intake/forms/${appointmentId}/submit`, {
        method: "POST",
        body: JSON.stringify({ answers }),
      });

      if (res?.ok === false && res?.errors) {
        // --- Validation errors: highlight fields, stay on page, preserve answers
        setErrors(res.errors);
        return;
      }

      // --- Success:
      if (res?.next === "consent" && res?.request_id) {
        // Go to e-sign flow; include appt in query so consent page can deep-link back to docs
        return nav(`/consent/${res.request_id}?appt=${res.appointment_id || appointmentId}`);
      }
      // Default: go to docs for this appointment
      return nav(`/docs?appt=${appointmentId}`);
    } catch (e: any) {
      // --- Server/network failure: show toast; preserve answers; keep button enabled
      setMsg(e.message || "Submission failed");
    }
  }

  if (loading) return <div className="p-6">Loading forms…</div>;

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Digital intake</h2>

      {forms.length === 0 && <p className="text-gray-400 mb-4">No forms assigned.</p>}

      <div className="space-y-6">
        {forms.map((f) => {
          const props = f.schema?.properties || {
            name: { title: "Full name", type: "string" },
            insurance_id: { title: "Insurance ID", type: "string" },
          };
          const required = new Set(f.schema?.required || []);
          return (
            <fieldset key={f.id} className="border p-3">
              <legend className="font-semibold">{f.title}</legend>
              {Object.entries(props).map(([field, meta]) => {
                const key = `${f.id}.${field}`;
                const showErr = Boolean(errors[key]);
                return (
                  <div className="mt-2" key={field}>
                    <label className="block text-sm">
                      {meta.title || field} {required.has(field) && <span className="text-red-500">*</span>}
                    </label>
                    <input
                      className={`border p-2 w-full ${showErr ? "border-red-500" : ""}`}
                      onChange={(e) => onChange(f.id, field, e.target.value)}
                    />
                    {showErr && <p className="text-red-500 text-xs mt-1">{errors[key]}</p>}
                  </div>
                );
              })}
            </fieldset>
          );
        })}
      </div>

      <div className="mt-4 space-x-2">
        <button onClick={submit} className="border px-3 py-1">Submit</button>
        <Link to={`/confirm?aid=${appointmentId}`} className="border px-3 py-1">Back</Link>
      </div>

      {msg && <p className="text-red-400 mt-3">{msg}</p>}
    </div>
  );
}
