// apps/web/src/components/RoleGuard.tsx
import { useEffect, useState } from "react";
import { useLocation, Navigate } from "react-router-dom";
import { getMe, Role } from "../lib/auth";

/**
 * Central gate: checks the current path against the allowed list of the
 * logged-in persona. If ANON, allow only Home/Login.
 */
const ALLOW: Record<Role, RegExp[]> = {
  ANON: [
    /^\/$/, /^\/login$/, /^\/book$/, /^\/confirm$/,
  ],
  PATIENT: [
    /^\/$/, /^\/login$/, /^\/book$/, /^\/confirm$/,
    /^\/intake\/\d+$/, /^\/consent\/[^/]+$/, /^\/docs$/,
    /^\/check-in$/, /^\/portal\/summary\/[^/]+$/,
    /^\/portal\/follow-up$/, /^\/portal\/tasks$/,
  ],
  CLINICIAN: [
    /^\/provider\/prechart\/\d+$/, /^\/provider\/scribe\/\d+$/,
    /^\/portal\/summary\/[^/]+$/,
    /^\/billing\/cases$/, /^\/billing\/claims\/\d+$/,
  ],
  OPS: [
    /^\/ops\/queue$/, /^\/admin\/billing\/eligibility$/, /^\/admin\/tasks$/,
    /^\/ops\/escalations$/,
    /^\/admin\/compliance\/audit$/, /^\/admin\/compliance\/pia$/, /^\/admin\/compliance\/retention$/,
    /^\/admin\/analytics$/, /^\/admin\/experiments$/,
  ],
};

export function RoleGuard({ children }: { children: JSX.Element }) {
  const loc = useLocation();
  const [role, setRole] = useState<Role | null>(null);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        setErr("");
        const me = await getMe();
        setRole((me.role as Role) || "ANON");
      } catch (e: any) {
        setErr(e.message || "Cannot determine identity.");
        setRole("ANON");
      }
    })();
  }, []);

  if (role === null) return <div className="p-6">Checking access…</div>;
  const patterns = ALLOW[role] ?? [];
  const allowed = patterns.some((rx) => rx.test(loc.pathname));

  // Always allow "/" and "/login" (helpful UX for switching persona)
  if (loc.pathname === "/" || loc.pathname === "/login") return children;

  if (!allowed) {
    return (
      <div className="p-6 space-y-3">
        <div className="text-red-600">Not authorized for: <code>{loc.pathname}</code></div>
        <div className="text-sm text-gray-500">
          Signed in as <b>{role}</b>. Go to <a className="underline" href="/">Home</a> or <a className="underline" href="/login">Login</a>.
        </div>
        {err && <div className="text-xs text-gray-400">{err}</div>}
      </div>
    );
  }
  return children;
}
